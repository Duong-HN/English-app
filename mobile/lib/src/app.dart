import 'package:flutter/material.dart';

import 'core/api_client.dart';
import 'core/auth_controller.dart';
import 'core/token_store.dart';
import 'features/auth/auth_page.dart';
import 'features/home/home_page.dart';
import 'features/onboarding/onboarding_page.dart';

class LearnMateApp extends StatefulWidget {
  const LearnMateApp({super.key, this.apiClient, this.tokenStore});

  final ApiClient? apiClient;
  final TokenStore? tokenStore;

  @override
  State<LearnMateApp> createState() => _LearnMateAppState();
}

class _LearnMateAppState extends State<LearnMateApp> {
  late final AuthController _authController;

  @override
  void initState() {
    super.initState();
    _authController = AuthController(
      apiClient: widget.apiClient ?? ApiClient(),
      tokenStore: widget.tokenStore ?? const SecureTokenStore(),
    );
    _authController.initialize();
  }

  @override
  void dispose() {
    _authController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LearnMate AI',
      debugShowCheckedModeBanner: false,
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
          if (role != null && role.isNotEmpty && role != 'learner') {
            return _NonLearnerPage(role: role, authController: _authController);
          }
          return _LearnerEntry(authController: _authController);
        },
      ),
    );
  }
}

class _LearnerEntry extends StatefulWidget {
  const _LearnerEntry({required this.authController});

  final AuthController authController;

  @override
  State<_LearnerEntry> createState() => _LearnerEntryState();
}

class _LearnerEntryState extends State<_LearnerEntry> {
  bool _onboardingCompleted = false;

  @override
  Widget build(BuildContext context) {
    if (_onboardingCompleted) {
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
