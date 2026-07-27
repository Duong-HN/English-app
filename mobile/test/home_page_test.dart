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

AuthController authenticatedController(ApiClient apiClient) {
  apiClient.accessToken = 'learner-token';
  return AuthController(apiClient: apiClient, tokenStore: MemoryTokenStore())
    ..user = {
      'id': 'learner-1',
      'email': 'learner@example.com',
      'display_name': 'Test Learner',
      'role': 'learner',
    };
}

http.Response jsonResponse(Object body, int status) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);

void main() {
  testWidgets('home combines the personal route with teacher assignments', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/home') {
          return jsonResponse({
            'daily_minutes': 30,
            'personal_learning_path': {
              'id': 'path-1',
              'goal': 'IELTS 6.5',
              'current_level': 'B1',
              'minutes_per_day': 30,
              'plan': <String, dynamic>{},
            },
            'next_personal_task': {
              'title': 'Ôn từ vựng theo chủ đề',
              'skill': 'reading',
              'duration_minutes': 15,
            },
            'class_assignments': [
              {
                'id': 'assignment-1',
                'title': 'Speaking: Describe your hometown',
                'skill': 'speaking',
                'estimated_minutes': 15,
              },
            ],
          }, 200);
        }
        if (request.url.path == '/api/v1/classes') {
          return jsonResponse({'items': <Map<String, dynamic>>[]}, 200);
        }
        if (request.url.path == '/api/v1/analyses') {
          return jsonResponse({'items': <Map<String, dynamic>>[]}, 200);
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

    expect(find.byKey(const Key('home-dashboard')), findsOneWidget);
    expect(find.text('IELTS 6.5'), findsOneWidget);
    expect(find.text('Ôn từ vựng theo chủ đề'), findsOneWidget);
    expect(find.text('Speaking: Describe your hometown'), findsOneWidget);
    expect(find.text('Làm bài từ lớp'), findsOneWidget);
    await tester.tap(find.byKey(const Key('continue-learning')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('class-invite-code')), findsOneWidget);
  });

  testWidgets('personal Continue opens contextual Study and records its day', (
    tester,
  ) async {
    final analysisBodies = <Map<String, dynamic>>[];
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'GET' && request.url.path == '/api/v1/home') {
          return jsonResponse({
            'daily_minutes': 30,
            'class_assignments': <Map<String, dynamic>>[],
            'personal_learning_path': {
              'id': 'path-1',
              'goal': 'Improve writing',
              'current_level': 'B1',
              'minutes_per_day': 30,
              'plan': <String, dynamic>{},
            },
            'next_personal_task': {
              'learning_path_id': 'path-1',
              'day': 3,
              'title': 'Write a short introduction',
              'skill': 'writing',
              'activity': 'Write one paragraph about yourself.',
              'duration_minutes': 20,
              'success_criteria': 'Write at least five sentences.',
            },
          }, 200);
        }
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/analyses/writing') {
          analysisBodies.add(jsonDecode(request.body) as Map<String, dynamic>);
          return jsonResponse({
            'result': {'score': 8, 'summary': 'Clear introduction.'},
          }, 201);
        }
        if (request.url.path == '/api/v1/classes' ||
            request.url.path == '/api/v1/analyses') {
          return jsonResponse({'items': <Map<String, dynamic>>[]}, 200);
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

    await tester.tap(find.byKey(const Key('continue-learning')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('personal-task-context')), findsOneWidget);
    expect(find.text('Write a short introduction'), findsOneWidget);
    final mode = tester.widget<SegmentedButton<String>>(
      find.byType(SegmentedButton<String>),
    );
    expect(mode.selected, {'writing'});

    await tester.enterText(
      find.byKey(const Key('study-input')),
      'I am a student and I enjoy learning English every day.',
    );
    final analyzeButton = find.byKey(const Key('analyze-study'));
    await tester.drag(
      find.byKey(const Key('study-page')),
      const Offset(0, -260),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(analyzeButton);
    await tester.tap(analyzeButton);
    await tester.pumpAndSettle();

    expect(analysisBodies.single['learning_path_id'], 'path-1');
    expect(analysisBodies.single['task_day'], 3);
    expect(
      find.text('Đã ghi nhận tiến độ', skipOffstage: false),
      findsOneWidget,
    );

    await tester.tap(find.text('Home'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Học'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('personal-task-context')), findsNothing);
    await tester.enterText(
      find.byKey(const Key('study-input')),
      'This is another generic writing sample.',
    );
    await tester.ensureVisible(analyzeButton);
    await tester.tap(analyzeButton);
    await tester.pumpAndSettle();

    expect(analysisBodies, hasLength(2));
    expect(analysisBodies.last.containsKey('learning_path_id'), isFalse);
    expect(analysisBodies.last.containsKey('task_day'), isFalse);
  });

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

    await tester.tap(find.text('Học'));
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
        if (request.method == 'GET' && request.url.path == '/api/v1/home') {
          return jsonResponse({
            'daily_minutes': 30,
            'personal_tasks': <Map<String, dynamic>>[],
            'class_tasks': <Map<String, dynamic>>[],
          }, 200);
        }
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

    await tester.drag(
      find.byKey(const Key('home-dashboard')),
      const Offset(0, -180),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('open-learning-path')));
    await tester.tap(find.byKey(const Key('open-learning-path')));
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

    await tester.drag(
      find.byKey(const Key('home-dashboard')),
      const Offset(0, -180),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('open-learning-path')));
    await tester.tap(find.byKey(const Key('open-learning-path')));
    await tester.pumpAndSettle();

    final goalField = tester.widget<TextField>(
      find.byKey(const Key('learning-path-goal')),
    );
    expect(goalField.controller?.text, 'Chuẩn bị phỏng vấn bằng tiếng Anh');
    expect(find.text('A2'), findsOneWidget);
    expect(find.text('20 phút'), findsOneWidget);
    expect(find.text('Lộ trình đã lưu.'), findsOneWidget);
  });

  testWidgets('flashcard opens the vocabulary detail lookup', (tester) async {
    final requestedPaths = <String>[];
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        requestedPaths.add(request.url.path);
        if (request.url.path == '/api/v1/home') {
          return jsonResponse({
            'daily_minutes': 30,
            'personal_tasks': <Map<String, dynamic>>[],
            'class_tasks': <Map<String, dynamic>>[],
          }, 200);
        }
        if (request.url.path == '/api/v1/classes' ||
            request.url.path == '/api/v1/analyses') {
          return jsonResponse({'items': <Map<String, dynamic>>[]}, 200);
        }
        if (request.url.path == '/api/v1/analyses/reading') {
          return jsonResponse({
            'result': {
              'summary': 'A short greeting.',
              'vocabulary': [
                {
                  'word': 'hello',
                  'meaning': 'xin chào',
                  'example': 'Hello, everyone!',
                },
              ],
            },
          }, 201);
        }
        if (request.url.path == '/api/v1/vocabulary/lookup/hello') {
          return jsonResponse({
            'word': 'hello',
            'phonetics': [
              {'text': '/həˈləʊ/', 'audio_url': null},
            ],
            'meanings': [
              {
                'part_of_speech': 'exclamation',
                'definitions': ['Used as a greeting.'],
                'examples': ['Hello, everyone!'],
              },
            ],
            'synonyms': ['hi'],
            'antonyms': <String>[],
            'collocations': ['say hello'],
            'cached': false,
          }, 200);
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

    await tester.tap(find.text('Học'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('study-input')),
      'Hello, everyone. This is a short reading passage.',
    );
    await tester.drag(
      find.byKey(const Key('study-page')),
      const Offset(0, -180),
    );
    await tester.pumpAndSettle();
    final analyzeButton = find.byKey(const Key('analyze-study'));
    await tester.tap(analyzeButton);
    await tester.pumpAndSettle();

    await tester.drag(
      find.byKey(const Key('study-page')),
      const Offset(0, -500),
    );
    await tester.pumpAndSettle();
    final detailsButton = find.byKey(const Key('view-word-details-hello'));
    await tester.ensureVisible(detailsButton);
    await tester.tap(detailsButton);
    await tester.pumpAndSettle();

    expect(requestedPaths, contains('/api/v1/vocabulary/lookup/hello'));
    expect(find.text('Chi tiết từ vựng'), findsOneWidget);
    expect(find.text('/həˈləʊ/'), findsOneWidget);
    expect(find.byKey(const Key('collocation-say hello')), findsOneWidget);
  });
}
