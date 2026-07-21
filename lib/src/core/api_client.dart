import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;

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

  Future<Map<String, dynamic>> analyze({
    required String type,
    required String inputText,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/v1/analyses/$type'),
      headers: const {
        'Content-Type': 'application/json',
        'X-Dev-User': 'demo-user',
      },
      body: jsonEncode({'input_text': inputText}),
    );

    final payload = _decode(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(payload['detail']?.toString() ?? 'API request failed');
    }
    return payload;
  }

  Future<List<Map<String, dynamic>>> history() async {
    final response = await _client.get(
      Uri.parse('$baseUrl/api/v1/analyses'),
      headers: const {'X-Dev-User': 'demo-user'},
    );
    final payload = _decode(response);
    if (response.statusCode != 200) {
      throw ApiException(
        payload['detail']?.toString() ?? 'Could not load history',
      );
    }
    return (payload['items'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  Map<String, dynamic> _decode(http.Response response) {
    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      return {'detail': 'Invalid server response (${response.statusCode})'};
    }
  }
}
