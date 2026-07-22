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

  test('classroom list and join use the learner bearer contract', () async {
    var joined = false;
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer learner-token');
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/classes/mine') {
          expect(request.url.queryParameters, {'limit': '100', 'offset': '0'});
          return http.Response(
            jsonEncode({
              'items': joined
                  ? [
                      {
                        'id': 'class-1',
                        'name': 'English Club',
                        'membership_status': 'pending',
                      },
                    ]
                  : <Map<String, dynamic>>[],
              'total': joined ? 1 : 0,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        expect(request.method, 'POST');
        expect(request.url.path, '/api/v1/classes/join');
        expect(jsonDecode(request.body), {'join_code': 'ABC123'});
        joined = true;
        return http.Response(
          jsonEncode({
            'id': 'class-1',
            'name': 'English Club',
            'membership_status': 'pending',
          }),
          201,
          headers: {'content-type': 'application/json'},
        );
      }),
    )..accessToken = 'learner-token';

    expect(await client.myClasses(), isEmpty);
    final joinedClass = await client.joinClass('ABC123');
    expect(joinedClass['membership_status'], 'pending');
    expect(await client.myClasses(), hasLength(1));
  });

  test('classroom lists load every server page', () async {
    final offsets = <String>[];
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        final offset = request.url.queryParameters['offset']!;
        offsets.add(offset);
        final start = int.parse(offset);
        final count = start == 0 ? 100 : 1;
        return http.Response(
          jsonEncode({
            'items': List.generate(
              count,
              (index) => {'id': 'class-${start + index + 1}'},
            ),
            'total': 101,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    )..accessToken = 'learner-token';

    final classes = await client.myClasses();

    expect(classes, hasLength(101));
    expect(offsets, ['0', '100']);
  });

  test(
    'assignment list, submission and leave use exact classroom paths',
    () async {
      final seen = <String>[];
      final client = ApiClient(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer learner-token');
          seen.add('${request.method} ${request.url.path}');
          if (request.method == 'GET') {
            expect(request.url.queryParameters, {
              'limit': '100',
              'offset': '0',
            });
            return http.Response(
              jsonEncode({
                'items': [
                  {
                    'id': 'assignment-1',
                    'class_id': 'class-1',
                    'title': 'Writing practice',
                    'skill_type': 'writing',
                    'status': 'published',
                  },
                ],
                'total': 1,
              }),
              200,
              headers: {'content-type': 'application/json'},
            );
          }
          if (request.method == 'POST') {
            expect(jsonDecode(request.body), {'analysis_id': 'analysis-1'});
            return http.Response(
              jsonEncode({
                'id': 'submission-1',
                'assignment_id': 'assignment-1',
                'analysis_id': 'analysis-1',
              }),
              201,
              headers: {'content-type': 'application/json'},
            );
          }
          return http.Response(
            jsonEncode({'message': 'Membership deleted'}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      )..accessToken = 'learner-token';

      final assignments = await client.classAssignments('class-1');
      expect(assignments.single['skill_type'], 'writing');
      final submission = await client.submitAssignment(
        assignmentId: 'assignment-1',
        analysisId: 'analysis-1',
      );
      expect(submission['id'], 'submission-1');
      await client.leaveClass('class-1');

      expect(seen, [
        'GET /api/v1/classes/class-1/assignments',
        'POST /api/v1/assignments/assignment-1/submissions',
        'DELETE /api/v1/classes/class-1/membership',
      ]);
    },
  );
}
