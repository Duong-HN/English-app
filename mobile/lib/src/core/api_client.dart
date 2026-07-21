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
    return (payload['items'] as List<dynamic>).cast<Map<String, dynamic>>();
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

  void close() => _client.close();
}
