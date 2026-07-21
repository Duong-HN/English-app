import 'package:flutter/material.dart';

import 'core/api_client.dart';
import 'core/auth_controller.dart';
import 'core/token_store.dart';
import 'features/auth/auth_page.dart';
import 'features/home/home_page.dart';

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
          return HomePage(
            apiClient: _authController.apiClient,
            authController: _authController,
          );
        },
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
