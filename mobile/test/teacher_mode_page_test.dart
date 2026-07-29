import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/link.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/core/app_config.dart';
import 'package:english_ai_tutor/src/core/auth_controller.dart';
import 'package:english_ai_tutor/src/core/token_store.dart';
import 'package:english_ai_tutor/src/features/teacher/teacher_mode_page.dart';

void main() {
  final originalLauncher = UrlLauncherPlatform.instance;

  tearDown(() {
    UrlLauncherPlatform.instance = originalLauncher;
  });

  test('dashboard URL accepts only HTTP(S) URLs with a host', () {
    expect(
      AppConfig.parseTeacherDashboardUrl(
        'https://dashboard.example.test/teacher',
      ),
      Uri.parse('https://dashboard.example.test/teacher'),
    );
    expect(AppConfig.parseTeacherDashboardUrl(''), isNull);
    expect(AppConfig.parseTeacherDashboardUrl('javascript:alert(1)'), isNull);
    expect(AppConfig.parseTeacherDashboardUrl('/teacher'), isNull);
  });

  testWidgets('approved teacher can open the configured Teacher Dashboard', (
    tester,
  ) async {
    final launcher = _FakeUrlLauncher();
    UrlLauncherPlatform.instance = launcher;
    final controller = _teacherController();
    addTearDown(controller.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: TeacherModePage(
          authController: controller,
          teacherDashboardUrl: 'https://dashboard.example.test/teacher',
        ),
      ),
    );

    expect(find.byKey(const Key('open-teacher-dashboard')), findsOneWidget);
    await tester.tap(find.byKey(const Key('open-teacher-dashboard')));
    await tester.pumpAndSettle();

    expect(launcher.lastUrl, 'https://dashboard.example.test/teacher');
    expect(launcher.lastOptions?.mode, PreferredLaunchMode.externalApplication);
  });

  testWidgets(
    'invalid dashboard URL shows an error and learner switch remains',
    (tester) async {
      final controller = _teacherController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        MaterialApp(
          home: TeacherModePage(
            authController: controller,
            teacherDashboardUrl: 'javascript:alert(1)',
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('open-teacher-dashboard')));
      await tester.pump();

      expect(
        find.text('Không thể mở Teacher Dashboard. Kiểm tra URL và thử lại.'),
        findsOneWidget,
      );
      expect(find.byKey(const Key('switch-to-learner-mode')), findsOneWidget);

      await tester.tap(find.byKey(const Key('switch-to-learner-mode')));
      expect(controller.activeMode, AuthController.learnerMode);
    },
  );
}

AuthController _teacherController() {
  final apiClient = ApiClient(baseUrl: 'https://api.example.test');
  apiClient.accessToken = 'teacher-token';
  return AuthController(apiClient: apiClient, tokenStore: MemoryTokenStore())
    ..user = {
      'id': 'teacher-1',
      'email': 'teacher@example.com',
      'display_name': 'Teacher',
      'role': 'teacher',
    };
}

class _FakeUrlLauncher extends UrlLauncherPlatform {
  String? lastUrl;
  LaunchOptions? lastOptions;

  @override
  LinkDelegate? get linkDelegate => null;

  @override
  Future<bool> launchUrl(String url, LaunchOptions options) async {
    lastUrl = url;
    lastOptions = options;
    return true;
  }
}
