import 'package:flutter/foundation.dart';

import 'api_client.dart';
import 'token_store.dart';

class AuthController extends ChangeNotifier {
  AuthController({required this.apiClient, required this.tokenStore});

  static const learnerMode = 'learner';
  static const teacherMode = 'teacher';

  final ApiClient apiClient;
  final TokenStore tokenStore;

  Map<String, dynamic>? user;
  bool initialized = false;
  bool loading = false;
  String? error;
  String activeMode = learnerMode;

  bool get isAuthenticated => user != null && apiClient.accessToken != null;
  bool get canUseTeacherMode =>
      user?['role']?.toString().toLowerCase() == teacherMode;

  void setActiveMode(String mode) {
    if (mode == teacherMode && !canUseTeacherMode) return;
    if (mode != learnerMode && mode != teacherMode) return;
    if (activeMode == mode) return;
    activeMode = mode;
    notifyListeners();
  }

  Future<void> initialize() async {
    final token = await tokenStore.read();
    if (token != null) {
      apiClient.accessToken = token;
      try {
        user = await apiClient.profile();
        if (!canUseTeacherMode) activeMode = learnerMode;
      } on ApiException catch (exception) {
        if (exception.statusCode == 401) {
          await tokenStore.clear();
          apiClient.accessToken = null;
        } else {
          error = exception.message;
        }
      } catch (_) {
        error =
            'Không thể khôi phục phiên đăng nhập khi máy chủ đang ngoại tuyến.';
      }
    }
    initialized = true;
    notifyListeners();
  }

  Future<bool> login({required String email, required String password}) {
    return _authenticate(
      () => apiClient.login(email: email.trim(), password: password),
    );
  }

  Future<bool> register({
    required String email,
    required String password,
    required String displayName,
  }) {
    return _authenticate(
      () => apiClient.register(
        email: email.trim(),
        password: password,
        displayName: displayName.trim(),
      ),
    );
  }

  Future<bool> _authenticate(
    Future<Map<String, dynamic>> Function() request,
  ) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final session = await request();
      final token = session['access_token'] as String;
      apiClient.accessToken = token;
      user = session['user'] as Map<String, dynamic>;
      activeMode = learnerMode;
      await tokenStore.write(token);
      return true;
    } on ApiException catch (exception) {
      error = exception.message;
      return false;
    } catch (_) {
      error = 'Không thể kết nối máy chủ. Hãy kiểm tra backend và thử lại.';
      return false;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    user = null;
    apiClient.accessToken = null;
    activeMode = learnerMode;
    error = null;
    await tokenStore.clear();
    notifyListeners();
  }

  void clearError() {
    error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    apiClient.close();
    super.dispose();
  }
}
