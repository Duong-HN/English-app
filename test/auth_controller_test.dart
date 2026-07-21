import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/core/auth_controller.dart';
import 'package:english_ai_tutor/src/core/token_store.dart';

void main() {
  test('successful login stores token and user', () async {
    final store = MemoryTokenStore();
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient(
        (_) async => http.Response(
          jsonEncode({
            'access_token': 'access-token',
            'user': {
              'id': 'user-1',
              'email': 'learner@example.com',
              'display_name': 'Learner',
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        ),
      ),
    );
    final controller = AuthController(apiClient: apiClient, tokenStore: store);

    final success = await controller.login(
      email: 'learner@example.com',
      password: 'password-123',
    );

    expect(success, isTrue);
    expect(controller.isAuthenticated, isTrue);
    expect(await store.read(), 'access-token');
    expect(controller.user?['email'], 'learner@example.com');
    controller.dispose();
  });
}
