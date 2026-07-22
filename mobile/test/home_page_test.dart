import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image_picker/image_picker.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/core/auth_controller.dart';
import 'package:english_ai_tutor/src/core/ocr_service.dart';
import 'package:english_ai_tutor/src/core/speech_service.dart';
import 'package:english_ai_tutor/src/core/token_store.dart';
import 'package:english_ai_tutor/src/features/home/home_page.dart';

class FakeOcrService implements OcrService {
  @override
  bool get isSupported => true;

  @override
  Future<String?> recognize(ImageSource source) async =>
      'Recognized English text';
}

class FakeSpeechService implements SpeechService {
  bool _listening = false;

  @override
  bool get isListening => _listening;

  @override
  Future<bool> start({
    required void Function(String text) onText,
    required void Function(String message) onError,
    required void Function(bool listening) onListeningChanged,
  }) async {
    _listening = true;
    onListeningChanged(true);
    onText('I practice English every day');
    return true;
  }

  @override
  Future<void> stop() async => _listening = false;
}

AuthController authenticatedController(
  ApiClient apiClient, {
  String role = 'learner',
}) {
  apiClient.accessToken = 'learner-token';
  return AuthController(apiClient: apiClient, tokenStore: MemoryTokenStore())
    ..user = {
      'id': 'learner-1',
      'email': 'learner@example.com',
      'display_name': 'Test Learner',
      'role': role,
    };
}

http.Response jsonResponse(Object body, int status) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);

void main() {
  testWidgets('OCR and speech recognition feed editable English text', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient(
        (_) async => jsonResponse({'detail': 'Learning path not found'}, 404),
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: HomePage(
          apiClient: apiClient,
          authController: authenticatedController(apiClient),
          ocrService: FakeOcrService(),
          speechService: FakeSpeechService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Chụp ảnh OCR'));
    await tester.pumpAndSettle();
    TextField studyField = tester
        .widgetList<TextField>(find.byType(TextField))
        .firstWhere((field) => field.minLines == 5);
    expect(studyField.controller?.text, 'Recognized English text');

    await tester.tap(find.text('Nói'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Bắt đầu nói'));
    await tester.pumpAndSettle();
    studyField = tester
        .widgetList<TextField>(find.byType(TextField))
        .firstWhere((field) => field.minLines == 5);
    expect(studyField.controller?.text, 'I practice English every day');
    expect(
      find.text('Chấm nội dung transcript, không chấm phát âm.'),
      findsNothing,
    );
  });

  testWidgets('learner can generate and view a seven-day learning path', (
    tester,
  ) async {
    final tasks = List.generate(
      7,
      (index) => {
        'day': index + 1,
        'title': 'Ngày ${index + 1}',
        'skill': 'writing',
        'activity': 'Viết và sửa một đoạn văn ngắn.',
        'duration_minutes': 30,
        'success_criteria': 'Hoàn thành một bản sửa.',
      },
    );
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'GET' && request.url.path.endsWith('/current')) {
          return jsonResponse({'detail': 'Learning path not found'}, 404);
        }
        if (request.method == 'POST' &&
            request.url.path.endsWith('/generate')) {
          expect(request.headers['Authorization'], 'Bearer learner-token');
          return jsonResponse({
            'id': 'path-1',
            'goal': 'Giao tiếp tiếng Anh tự tin trong học tập và công việc',
            'current_level': 'B1',
            'minutes_per_day': 30,
            'provider': 'mock',
            'created_at': '2026-07-22T00:00:00Z',
            'plan': {
              'summary': 'Lộ trình thực tế dựa trên lịch sử học.',
              'weekly_goal': 'Học đủ bảy ngày.',
              'focus_areas': ['viết'],
              'personalization_notes': ['Ưu tiên kỹ năng đang ít thực hành.'],
              'daily_tasks': tasks,
              'checkpoints': ['So sánh ngày 1 và ngày 7.'],
            },
          }, 201);
        }
        return jsonResponse({'detail': 'Unexpected request'}, 500);
      }),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: HomePage(
          apiClient: apiClient,
          authController: authenticatedController(apiClient),
          ocrService: FakeOcrService(),
          speechService: FakeSpeechService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Lộ trình'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('generate-learning-path')));
    await tester.pumpAndSettle();

    expect(find.text('Lộ trình thực tế dựa trên lịch sử học.'), findsOneWidget);
    expect(find.text('Nhiệm vụ 7 ngày'), findsOneWidget);
    expect(find.text('Ngày 1'), findsOneWidget);
  });

  testWidgets('stored learning path restores goal, level and daily minutes', (
    tester,
  ) async {
    final tasks = List.generate(
      7,
      (index) => {
        'day': index + 1,
        'title': 'Ngày ${index + 1}',
        'skill': 'speaking',
        'activity': 'Luyện trả lời một câu hỏi giao tiếp.',
        'duration_minutes': 20,
        'success_criteria': 'Trả lời đủ ý và tự sửa transcript.',
      },
    );
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient(
        (_) async => jsonResponse({
          'id': 'stored-path',
          'goal': 'Chuẩn bị phỏng vấn bằng tiếng Anh',
          'current_level': 'A2',
          'minutes_per_day': 20,
          'provider': 'mock',
          'created_at': '2026-07-22T00:00:00Z',
          'plan': {
            'summary': 'Lộ trình đã lưu.',
            'weekly_goal': 'Luyện tập đều đặn.',
            'focus_areas': ['giao tiếp'],
            'personalization_notes': <String>[],
            'daily_tasks': tasks,
            'checkpoints': ['So sánh ngày 1 và ngày 7.'],
          },
        }, 200),
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: HomePage(
          apiClient: apiClient,
          authController: authenticatedController(apiClient),
          ocrService: FakeOcrService(),
          speechService: FakeSpeechService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Lộ trình'));
    await tester.pumpAndSettle();

    final goalField = tester.widget<TextField>(
      find.byKey(const Key('learning-path-goal')),
    );
    expect(goalField.controller?.text, 'Chuẩn bị phỏng vấn bằng tiếng Anh');
    expect(find.text('A2'), findsOneWidget);
    expect(find.text('20 phút'), findsOneWidget);
    expect(find.text('Lộ trình đã lưu.'), findsOneWidget);
  });

  testWidgets('home navigation exposes the state-preserving classroom tab', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/classes/mine') {
          return jsonResponse({'items': [], 'total': 0}, 200);
        }
        if (request.url.path == '/api/v1/learning-paths/current') {
          return jsonResponse({'detail': 'Learning path not found'}, 404);
        }
        return jsonResponse({'items': [], 'total': 0}, 200);
      }),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: HomePage(
          apiClient: apiClient,
          authController: authenticatedController(apiClient),
          ocrService: FakeOcrService(),
          speechService: FakeSpeechService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(NavigationDestination), findsNWidgets(5));
    await tester.tap(find.text('Lớp học'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('classes-page')), findsOneWidget);
    expect(find.byKey(const Key('join-class')), findsOneWidget);
    expect(
      find.text('Bạn chưa tham gia lớp nào. Nhập mã lớp để bắt đầu.'),
      findsOneWidget,
    );
  });
}
