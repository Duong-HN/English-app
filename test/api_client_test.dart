import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';

void main() {
  test('login sends credentials without an authorization header', () async {
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.url.path, '/api/v1/auth/login');
        expect(request.headers['Authorization'], isNull);
        expect(jsonDecode(request.body)['email'], 'learner@example.com');
        return http.Response(
          jsonEncode({
            'access_token': 'token',
            'user': {'id': '1', 'email': 'learner@example.com'},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    );

    final response = await client.login(
      email: 'learner@example.com',
      password: 'password-123',
    );
    expect(response['access_token'], 'token');
  });

  test('authenticated analysis sends the bearer token', () async {
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer secret-token');
        return http.Response(
          jsonEncode({
            'result': {'summary': 'ok'},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    )..accessToken = 'secret-token';

    final response = await client.analyze(
      type: 'reading',
      inputText: 'English text',
    );
    expect((response['result'] as Map<String, dynamic>)['summary'], 'ok');
  });

  test('API validation detail becomes a readable exception', () async {
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient(
        (_) async => http.Response(
          jsonEncode({
            'detail': [
              {'msg': 'Input is too short'},
            ],
          }),
          422,
          headers: {'content-type': 'application/json'},
        ),
      ),
    );

    expect(
      () => client.analyze(type: 'writing', inputText: 'x'),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          'Input is too short',
        ),
      ),
    );
  });
}
