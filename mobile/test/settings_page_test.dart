import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/core/auth_controller.dart';
import 'package:english_ai_tutor/src/core/token_store.dart';
import 'package:english_ai_tutor/src/features/settings/settings_page.dart';
import 'package:english_ai_tutor/src/features/shared/learnmate_top_bar.dart';

void main() {
  testWidgets('learner opens teacher registration from Settings', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.method, 'GET');
        if (request.url.path == '/api/v1/learning-spaces') {
          return _jsonResponse({
            'items': [
              {
                'id': 'self-1',
                'kind': 'self',
                'name': 'Tự học',
                'current_level': 'B1',
              },
            ],
          });
        }
        expect(request.url.path, '/api/v1/teacher-applications/me');
        return _jsonResponse({'application': null});
      }),
    )..accessToken = 'learner-token';
    final controller = _controller(apiClient, role: 'learner');

    await tester.pumpWidget(
      MaterialApp(home: SettingsPage(authController: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Cài đặt'), findsOneWidget);
    expect(
      find.byKey(const Key('settings-teacher-application')),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('settings-teacher-application')));
    await tester.pumpAndSettle();

    expect(find.text('Đăng ký trở thành giáo viên'), findsOneWidget);
    expect(find.byKey(const Key('teacher-application-form')), findsOneWidget);
    controller.dispose();
  });

  testWidgets('teacher can choose teacher mode from Settings', (tester) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((_) async => _jsonResponse({})),
    )..accessToken = 'teacher-token';
    final controller = _controller(apiClient, role: 'teacher');

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: FilledButton(
              key: const Key('open-settings'),
              onPressed: () =>
                  Navigator.of(tester.element(find.byType(Scaffold))).push(
                    MaterialPageRoute<void>(
                      builder: (_) => SettingsPage(authController: controller),
                    ),
                  ),
              child: const Text('Mở cài đặt'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('open-settings')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('account-mode-switch')), findsOneWidget);
    await tester.tap(find.text('Giáo viên'));
    await tester.pumpAndSettle();

    expect(controller.activeMode, AuthController.teacherMode);
    controller.dispose();
  });

  testWidgets('learner can switch between self-study and a class space', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.url.path, '/api/v1/learning-spaces');
        return _jsonResponse({
          'items': [
            {
              'id': 'self-1',
              'kind': 'self',
              'name': 'Tự học',
              'current_level': 'B1',
            },
            {
              'id': 'class-1',
              'kind': 'class',
              'name': 'Lớp · IELTS 01',
              'class_id': 'class-1',
            },
          ],
        });
      }),
    )..accessToken = 'learner-token';
    final controller = _controller(apiClient, role: 'learner');

    await tester.pumpWidget(
      MaterialApp(home: SettingsPage(authController: controller)),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('learning-space-class-1')),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const ValueKey('learning-space-class-1')));
    await tester.pumpAndSettle();

    expect(controller.activeLearningSpaceId, 'class-1');
    expect(apiClient.learningSpaceId, 'class-1');
    controller.dispose();
  });

  testWidgets('top bar exposes settings and notifications actions', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((_) async => _jsonResponse({})),
    );
    final controller = _controller(apiClient, role: 'learner');
    var settingsOpened = false;
    var notificationsOpened = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          appBar: LearnMateTopBar(
            authController: controller,
            title: 'Tổng quan',
            onSettings: () => settingsOpened = true,
            onNotifications: () => notificationsOpened = true,
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('open-settings')));
    await tester.tap(find.byKey(const Key('open-notifications')));

    expect(settingsOpened, isTrue);
    expect(notificationsOpened, isTrue);
    controller.dispose();
  });
}

AuthController _controller(ApiClient apiClient, {required String role}) {
  return AuthController(apiClient: apiClient, tokenStore: MemoryTokenStore())
    ..user = {
      'id': '$role-1',
      'email': '$role@example.com',
      'display_name': role == 'teacher' ? 'Teacher' : 'Learner',
      'role': role,
    };
}

http.Response _jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
