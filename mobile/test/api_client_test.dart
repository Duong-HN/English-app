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

  test(
    'learning path generation sends personalized settings with bearer token',
    () async {
      late http.Request captured;
      final client = ApiClient(
        baseUrl: 'https://api.example.com',
        client: MockClient((request) async {
          captured = request;
          return http.Response(
            jsonEncode({
              'id': 'path-1',
              'goal': 'Improve speaking',
              'current_level': 'B1',
              'minutes_per_day': 30,
              'plan': <String, dynamic>{},
              'provider': 'mock',
              'created_at': '2026-07-22T00:00:00Z',
            }),
            201,
            headers: {'content-type': 'application/json'},
          );
        }),
      )..accessToken = 'learner-token';

      final response = await client.generateLearningPath(
        goal: 'Improve speaking',
        currentLevel: 'B1',
        minutesPerDay: 30,
      );

      expect(captured.url.path, '/api/v1/learning-paths/generate');
      expect(captured.headers['Authorization'], 'Bearer learner-token');
      expect(jsonDecode(captured.body), {
        'goal': 'Improve speaking',
        'current_level': 'B1',
        'minutes_per_day': 30,
      });
      expect(response['id'], 'path-1');
    },
  );

  test('onboarding preferences use the learner contract', () async {
    late http.Request captured;
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        captured = request;
        return jsonResponse({'status': 'needs_daily_time', 'goal': 'ielts'});
      }),
    )..accessToken = 'learner-token';

    final response = await client.updateOnboardingPreferences(goal: 'ielts');

    expect(captured.method, 'PATCH');
    expect(captured.url.path, '/api/v1/onboarding/preferences');
    expect(captured.headers['Authorization'], 'Bearer learner-token');
    expect(jsonDecode(captured.body), {'goal': 'ielts'});
    expect(response['status'], 'needs_daily_time');
  });

  test('class APIs accept bare lists and submit learner text', () async {
    final requests = <http.Request>[];
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        requests.add(request);
        if (request.method == 'GET') {
          return http.Response(
            jsonEncode([
              {'id': 'class-1', 'name': 'IELTS 01'},
            ]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return jsonResponse({'status': 'submitted', 'input_text': 'My answer'});
      }),
    )..accessToken = 'learner-token';

    final classes = await client.classes();
    final submission = await client.submitAssignment(
      assignmentId: 'assignment-1',
      inputText: 'My answer',
    );

    expect(classes.single['name'], 'IELTS 01');
    expect(requests.last.url.path, '/api/v1/assignments/assignment-1/submit');
    expect(jsonDecode(requests.last.body), {'input_text': 'My answer'});
    expect(submission['status'], 'submitted');
  });

  test('contextual analysis includes learning path and task day', () async {
    late http.Request captured;
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        captured = request;
        return jsonResponse({
          'result': {'summary': 'ok'},
        });
      }),
    )..accessToken = 'learner-token';

    await client.analyze(
      type: 'writing',
      inputText: 'My paragraph.',
      learningPathId: 'path-1',
      taskDay: 3,
    );

    expect(captured.url.path, '/api/v1/analyses/writing');
    expect(jsonDecode(captured.body), {
      'input_text': 'My paragraph.',
      'learning_path_id': 'path-1',
      'task_day': 3,
    });
  });

  test('existing learner submission uses the singular endpoint', () async {
    late http.Request captured;
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        captured = request;
        return jsonResponse({
          'id': 'submission-1',
          'assignment_id': 'assignment-1',
          'status': 'reviewed',
          'input_text': 'Saved answer',
          'teacher_feedback': 'Good work',
        });
      }),
    )..accessToken = 'learner-token';

    final response = await client.assignmentSubmission('assignment-1');

    expect(captured.url.path, '/api/v1/assignments/assignment-1/submission');
    expect(captured.headers['Authorization'], 'Bearer learner-token');
    expect(response['teacher_feedback'], 'Good work');
  });

  test(
    'word lookup encodes the path and sends learner authentication',
    () async {
      late http.Request captured;
      final client = ApiClient(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          captured = request;
          return jsonResponse({
            'word': "can't",
            'phonetics': <Map<String, dynamic>>[],
            'meanings': <Map<String, dynamic>>[],
            'synonyms': <String>[],
            'antonyms': <String>[],
            'collocations': <String>[],
            'cached': false,
          });
        }),
      )..accessToken = 'learner-token';

      final response = await client.lookupWord(" can't ");

      expect(captured.method, 'GET');
      expect(captured.url.pathSegments.last, "can't");
      expect(captured.url.path, "/api/v1/vocabulary/lookup/can't");
      expect(captured.headers['Authorization'], 'Bearer learner-token');
      expect(response['word'], "can't");
    },
  );
}

http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
