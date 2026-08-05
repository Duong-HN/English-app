import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/material.dart';

import 'core/api_client.dart';
import 'core/auth_controller.dart';
import 'core/push_notification_service.dart';
import 'core/token_store.dart';
import 'features/auth/auth_page.dart';
import 'features/home/home_page.dart';
import 'features/onboarding/onboarding_page.dart';
import 'features/groups/study_groups_page.dart';
import 'features/teacher/teacher_mode_page.dart';

class LearnMateApp extends StatefulWidget {
  const LearnMateApp({super.key, this.apiClient, this.tokenStore});

  final ApiClient? apiClient;
  final TokenStore? tokenStore;

  @override
  State<LearnMateApp> createState() => _LearnMateAppState();
}

class _LearnMateAppState extends State<LearnMateApp> {
  late final AuthController _authController;
  late final AppLinks _appLinks;
  StreamSubscription<Uri>? _deepLinkSubscription;
  late final PushNotificationService _pushNotificationService;
  final GlobalKey<ScaffoldMessengerState> _scaffoldMessengerKey =
      GlobalKey<ScaffoldMessengerState>();
  bool _pushStarted = false;
  String? _pendingInviteToken;

  @override
  void initState() {
    super.initState();
    _authController = AuthController(
      apiClient: widget.apiClient ?? ApiClient(),
      tokenStore: widget.tokenStore ?? const SecureTokenStore(),
    );
    _pushNotificationService = PushNotificationService(
      onForegroundMessage: _showForegroundPush,
    );
    _authController.addListener(_handleAuthChanged);
    _appLinks = AppLinks();
    _deepLinkSubscription = _appLinks.uriLinkStream.listen(_handleDeepLink);
    _appLinks.getInitialLink().then(_handleDeepLink);
    _authController.initialize();
  }

  void _handleAuthChanged() {
    if (!_authController.isAuthenticated || _pushStarted) return;
    _pushStarted = true;
    unawaited(_pushNotificationService.initialize(_authController.apiClient));
  }

  void _showForegroundPush(String title, String body) {
    if (!mounted) return;
    _scaffoldMessengerKey.currentState
      ?..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(body.isEmpty ? title : '$title\n$body'),
          duration: const Duration(seconds: 5),
        ),
      );
  }

  void _handleDeepLink(Uri? uri) {
    if (uri == null ||
        uri.scheme != 'learnmate' ||
        uri.host != 'study-groups') {
      return;
    }
    if (uri.path != '/join') return;
    final token = uri.queryParameters['token'];
    if (token == null || token.isEmpty || !mounted) return;
    setState(() => _pendingInviteToken = token);
  }

  @override
  void dispose() {
    _deepLinkSubscription?.cancel();
    _authController.removeListener(_handleAuthChanged);
    unawaited(_pushNotificationService.dispose());
    _authController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LearnMate AI',
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: _scaffoldMessengerKey,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2563EB),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
          fillColor: Colors.white,
        ),
        cardTheme: const CardThemeData(elevation: 0),
      ),
      home: AnimatedBuilder(
        animation: _authController,
        builder: (context, _) {
          if (!_authController.initialized) return const _SplashPage();
          if (!_authController.isAuthenticated) {
            return AuthPage(controller: _authController);
          }
          final role = _authController.user?['role']?.toString().toLowerCase();
          if (role == 'teacher' &&
              _authController.activeMode == AuthController.teacherMode) {
            return TeacherModePage(authController: _authController);
          }
          if (role != null &&
              role.isNotEmpty &&
              role != 'learner' &&
              role != 'teacher') {
            return _NonLearnerPage(role: role, authController: _authController);
          }
          return _LearnerEntry(
            authController: _authController,
            initialInviteToken: _pendingInviteToken,
            onInviteHandled: () => setState(() => _pendingInviteToken = null),
          );
        },
      ),
    );
  }
}

class _LearnerEntry extends StatefulWidget {
  const _LearnerEntry({
    required this.authController,
    this.initialInviteToken,
    this.onInviteHandled,
  });

  final AuthController authController;
  final String? initialInviteToken;
  final VoidCallback? onInviteHandled;

  @override
  State<_LearnerEntry> createState() => _LearnerEntryState();
}

class _LearnerEntryState extends State<_LearnerEntry> {
  bool _onboardingCompleted = false;
  bool _showInvite = false;

  @override
  void initState() {
    super.initState();
    _showInvite = widget.initialInviteToken != null;
  }

  @override
  void didUpdateWidget(covariant _LearnerEntry oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialInviteToken == null &&
        widget.initialInviteToken != null) {
      setState(() => _showInvite = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_onboardingCompleted) {
      if (_showInvite && widget.initialInviteToken != null) {
        return StudyGroupInvitePage(
          apiClient: widget.authController.apiClient,
          token: widget.initialInviteToken!,
          onCompleted: () {
            setState(() => _showInvite = false);
            widget.onInviteHandled?.call();
          },
        );
      }
      return HomePage(
        apiClient: widget.authController.apiClient,
        authController: widget.authController,
      );
    }
    return OnboardingPage(
      apiClient: widget.authController.apiClient,
      authController: widget.authController,
      onCompleted: () {
        if (mounted) setState(() => _onboardingCompleted = true);
      },
    );
  }
}

class _NonLearnerPage extends StatelessWidget {
  const _NonLearnerPage({required this.role, required this.authController});

  final String role;
  final AuthController authController;

  @override
  Widget build(BuildContext context) {
    final user = authController.user ?? const <String, dynamic>{};
    return Scaffold(
      appBar: AppBar(title: const Text('LearnMate AI')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.school_outlined, size: 64),
                const SizedBox(height: 16),
                Text(
                  user['display_name']?.toString() ?? 'Tài khoản LearnMate',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 6),
                Text(user['email']?.toString() ?? ''),
                const SizedBox(height: 16),
                Text(
                  role == 'teacher'
                      ? 'Tài khoản giáo viên không cần thực hiện onboarding của học viên. Hãy dùng Teacher Dashboard để quản lý lớp.'
                      : 'Tài khoản $role không cần thực hiện onboarding của học viên.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  onPressed: authController.logout,
                  icon: const Icon(Icons.logout),
                  label: const Text('Đăng xuất'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SplashPage extends StatelessWidget {
  const _SplashPage();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.school, size: 56, color: Color(0xFF2563EB)),
            SizedBox(height: 16),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
