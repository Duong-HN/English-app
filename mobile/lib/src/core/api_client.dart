import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      baseUrl =
          baseUrl ??
          const String.fromEnvironment(
            'API_BASE_URL',
            defaultValue: 'http://10.0.2.2:8000',
          );

  final http.Client _client;
  final String baseUrl;
  String? accessToken;

  static const _timeout = Duration(seconds: 30);

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    return _post(
      '/api/v1/auth/register',
      body: {'email': email, 'password': password, 'display_name': displayName},
      authenticated: false,
    );
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    return _post(
      '/api/v1/auth/login',
      body: {'email': email, 'password': password},
      authenticated: false,
    );
  }

  Future<Map<String, dynamic>> profile() => _get('/api/v1/auth/me');

  Future<Map<String, dynamic>> analyze({
    required String type,
    required String inputText,
    String? learningPathId,
    int? taskDay,
  }) {
    return _post(
      '/api/v1/analyses/$type',
      body: {
        'input_text': inputText,
        ...?(learningPathId == null
            ? null
            : {'learning_path_id': learningPathId}),
        ...?(taskDay == null ? null : {'task_day': taskDay}),
      },
    );
  }

  Future<List<Map<String, dynamic>>> history() async {
    final payload = await _get('/api/v1/analyses');
    return (payload['items'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> generateLearningPath({
    required String goal,
    required String currentLevel,
    required int minutesPerDay,
  }) {
    return _post(
      '/api/v1/learning-paths/generate',
      body: {
        'goal': goal,
        'current_level': currentLevel,
        'minutes_per_day': minutesPerDay,
      },
    );
  }

  Future<Map<String, dynamic>> currentLearningPath() {
    return _get('/api/v1/learning-paths/current');
  }

  Future<Map<String, dynamic>> updateDailyProgress({
    required String learningPathId,
    required int day,
    required bool completed,
    String? note,
  }) {
    return _patch(
      '/api/v1/learning-paths/$learningPathId/days/$day',
      body: {
        'completed': completed,
        ...?(note == null ? null : {'note': note}),
      },
    );
  }

  Future<Map<String, dynamic>> adaptLearningPath(String id) {
    return _post('/api/v1/learning-paths/$id/adapt', body: const {});
  }

  Future<Map<String, dynamic>> placementTest() =>
      _get('/api/v1/placement-test');

  Future<Map<String, dynamic>> submitPlacementTest(
    Map<String, String> answers,
  ) {
    return _post('/api/v1/placement-test/submit', body: {'answers': answers});
  }

  Future<Map<String, dynamic>> latestPlacementResult() {
    return _get('/api/v1/placement-test/latest');
  }

  Future<Map<String, dynamic>> onboarding() {
    return _get('/api/v1/onboarding');
  }

  Future<Map<String, dynamic>> updateOnboardingPreferences({
    String? goal,
    int? dailyMinutes,
  }) {
    return _patch(
      '/api/v1/onboarding/preferences',
      body: {
        ...?(goal == null ? null : {'goal': goal}),
        ...?(dailyMinutes == null ? null : {'daily_minutes': dailyMinutes}),
      },
    );
  }

  Future<Map<String, dynamic>> completeOnboarding() {
    return _post('/api/v1/onboarding/complete', body: const {});
  }

  Future<Map<String, dynamic>> teacherApplication() {
    return _get('/api/v1/teacher-applications/me');
  }

  Future<Map<String, dynamic>> submitTeacherApplication({
    required String motivation,
    String? organization,
  }) {
    return _post(
      '/api/v1/teacher-applications',
      body: {
        'motivation': motivation.trim(),
        ...?(organization == null || organization.trim().isEmpty
            ? null
            : {'organization': organization.trim()}),
      },
    );
  }

  Future<Map<String, dynamic>> home() {
    return _get('/api/v1/home');
  }

  Future<List<Map<String, dynamic>>> classes() async {
    final payload = await _get('/api/v1/classes');
    return _mapItems(payload, const ['items', 'classes', 'data']);
  }

  Future<Map<String, dynamic>> joinClass(String inviteCode) {
    return _post(
      '/api/v1/classes/join',
      body: {'invite_code': inviteCode.trim()},
    );
  }

  Future<List<Map<String, dynamic>>> classAssignments(String classId) async {
    final payload = await _get('/api/v1/classes/$classId/assignments');
    return _mapItems(payload, const ['items', 'assignments', 'tasks', 'data']);
  }

  Future<Map<String, dynamic>> submitAssignment({
    required String assignmentId,
    required String inputText,
  }) {
    return _post(
      '/api/v1/assignments/$assignmentId/submit',
      body: {'input_text': inputText},
    );
  }

  Future<Map<String, dynamic>> assignmentSubmission(String assignmentId) {
    return _get('/api/v1/assignments/$assignmentId/submission');
  }

  Future<Map<String, dynamic>> lookupWord(String word) {
    final encodedWord = Uri.encodeComponent(word.trim());
    return _get('/api/v1/vocabulary/lookup/$encodedWord');
  }

  Future<void> deleteAnalysis(String id) async {
    final response = await _client
        .delete(Uri.parse('$baseUrl/api/v1/analyses/$id'), headers: _headers())
        .timeout(_timeout);
    _decodeSuccess(response);
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _client
        .get(Uri.parse('$baseUrl$path'), headers: _headers())
        .timeout(_timeout);
    return _decodeSuccess(response);
  }

  Future<Map<String, dynamic>> _patch(
    String path, {
    required Map<String, dynamic> body,
  }) async {
    final response = await _client
        .patch(
          Uri.parse('$baseUrl$path'),
          headers: _headers(),
          body: jsonEncode(body),
        )
        .timeout(_timeout);
    return _decodeSuccess(response);
  }

  Future<Map<String, dynamic>> _post(
    String path, {
    required Map<String, dynamic> body,
    bool authenticated = true,
  }) async {
    final response = await _client
        .post(
          Uri.parse('$baseUrl$path'),
          headers: _headers(authenticated: authenticated),
          body: jsonEncode(body),
        )
        .timeout(_timeout);
    return _decodeSuccess(response);
  }

  Map<String, String> _headers({bool authenticated = true}) {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (authenticated && accessToken != null) {
      headers['Authorization'] = 'Bearer $accessToken';
    }
    return headers;
  }

  Map<String, dynamic> _decodeSuccess(http.Response response) {
    final payload = _decode(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _errorMessage(payload),
        statusCode: response.statusCode,
      );
    }
    return payload;
  }

  Map<String, dynamic> _decode(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) return decoded;
      if (decoded is List<dynamic>) return {'items': decoded};
      return {'detail': 'Invalid server response (${response.statusCode})'};
    } catch (_) {
      return {'detail': 'Invalid server response (${response.statusCode})'};
    }
  }

  List<Map<String, dynamic>> _mapItems(
    Map<String, dynamic> payload,
    List<String> keys,
  ) {
    for (final key in keys) {
      final value = payload[key];
      if (value is List) {
        return value.whereType<Map<String, dynamic>>().toList();
      }
      if (value is Map<String, dynamic>) {
        for (final nestedKey in keys) {
          final nested = value[nestedKey];
          if (nested is List) {
            return nested.whereType<Map<String, dynamic>>().toList();
          }
        }
      }
    }
    return const [];
  }

  String _errorMessage(Map<String, dynamic> payload) {
    final detail = payload['detail'];
    if (detail is String) return detail;
    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is Map<String, dynamic>) {
        return first['msg']?.toString() ?? 'Invalid request';
      }
    }
    return 'Request failed';
  }

  void close() => _client.close();
}
