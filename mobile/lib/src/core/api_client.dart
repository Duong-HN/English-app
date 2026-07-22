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
  }) {
    return _post('/api/v1/analyses/$type', body: {'input_text': inputText});
  }

  Future<List<Map<String, dynamic>>> history() async {
    final payload = await _get('/api/v1/analyses');
    return _items(payload);
  }

  Future<List<Map<String, dynamic>>> myClasses() async {
    return _allPages('/api/v1/classes/mine');
  }

  Future<Map<String, dynamic>> joinClass(String joinCode) {
    return _post('/api/v1/classes/join', body: {'join_code': joinCode});
  }

  Future<void> leaveClass(String classId) async {
    final response = await _client
        .delete(
          Uri.parse('$baseUrl/api/v1/classes/$classId/membership'),
          headers: _headers(),
        )
        .timeout(_timeout);
    _decodeSuccess(response);
  }

  Future<List<Map<String, dynamic>>> classAssignments(String classId) async {
    return _allPages('/api/v1/classes/$classId/assignments');
  }

  Future<Map<String, dynamic>> submitAssignment({
    required String assignmentId,
    required String analysisId,
  }) {
    return _post(
      '/api/v1/assignments/$assignmentId/submissions',
      body: {'analysis_id': analysisId},
    );
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

  Future<List<Map<String, dynamic>>> _allPages(String path) async {
    const pageSize = 100;
    final result = <Map<String, dynamic>>[];
    var offset = 0;
    while (true) {
      final separator = path.contains('?') ? '&' : '?';
      final payload = await _get(
        '$path${separator}limit=$pageSize&offset=$offset',
      );
      final page = _items(payload);
      result.addAll(page);
      final totalValue = payload['total'];
      final total = totalValue is num ? totalValue.toInt() : null;
      if (page.isEmpty ||
          page.length < pageSize ||
          (total != null && result.length >= total)) {
        return result;
      }
      offset += page.length;
    }
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
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      return {'detail': 'Invalid server response (${response.statusCode})'};
    }
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

  List<Map<String, dynamic>> _items(Map<String, dynamic> payload) {
    return (payload['items'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  void close() => _client.close();
}
