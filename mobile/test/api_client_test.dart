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
    final requestedPaths = <String>[];
    final statuses = <String>[];
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        requestedPaths.add(request.url.path);
        expect(request.headers['Authorization'], 'Bearer secret-token');
        if (request.method == 'POST') {
          expect(request.url.path, '/api/v1/analysis-jobs/reading');
          expect(request.headers['Idempotency-Key'], startsWith('mobile-'));
          return jsonResponse({'id': 'job-1', 'status': 'queued'});
        }
        if (request.url.path == '/api/v1/analysis-jobs/job-1') {
          return jsonResponse({
            'id': 'job-1',
            'status': 'succeeded',
            'analysis_id': 'analysis-1',
          });
        }
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
      onStatus: statuses.add,
    );
    expect((response['result'] as Map<String, dynamic>)['summary'], 'ok');
    expect(requestedPaths, [
      '/api/v1/analysis-jobs/reading',
      '/api/v1/analysis-jobs/job-1',
      '/api/v1/analyses/analysis-1',
    ]);
    expect(statuses, ['queued', 'succeeded']);
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
      final requests = <http.Request>[];
      final statuses = <String>[];
      final client = ApiClient(
        baseUrl: 'https://api.example.com',
        client: MockClient((request) async {
          requests.add(request);
          expect(request.headers['Authorization'], 'Bearer learner-token');
          if (request.method == 'POST') {
            expect(request.url.path, '/api/v1/learning-path-jobs');
            expect(
              request.headers['Idempotency-Key'],
              startsWith('mobile-learning-path-'),
            );
            expect(jsonDecode(request.body), {
              'goal': 'Improve speaking',
              'current_level': 'B1',
              'minutes_per_day': 30,
            });
            return jsonResponse({'id': 'job-1', 'status': 'queued'}, 202);
          }
          if (request.url.path == '/api/v1/learning-path-jobs/job-1') {
            return jsonResponse({
              'id': 'job-1',
              'status': 'succeeded',
              'learning_path_id': 'path-1',
            });
          }
          return jsonResponse({
            'id': 'path-1',
            'goal': 'Improve speaking',
            'current_level': 'B1',
            'minutes_per_day': 30,
            'plan': <String, dynamic>{},
            'provider': 'mock',
            'created_at': '2026-07-22T00:00:00Z',
          });
        }),
      )..accessToken = 'learner-token';

      final response = await client.generateLearningPath(
        goal: 'Improve speaking',
        currentLevel: 'B1',
        minutesPerDay: 30,
        onStatus: statuses.add,
      );

      expect(requests.map((request) => request.url.path), [
        '/api/v1/learning-path-jobs',
        '/api/v1/learning-path-jobs/job-1',
        '/api/v1/learning-paths/path-1',
      ]);
      expect(statuses, ['queued', 'succeeded']);
      expect(response['id'], 'path-1');
    },
  );

  test(
    'learning path adaptation uses a job and polls to the updated path',
    () async {
      final requests = <http.Request>[];
      final statuses = <String>[];
      final client = ApiClient(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'POST') {
            expect(request.url.path, '/api/v1/learning-path-jobs/path-1/adapt');
            expect(
              request.headers['Idempotency-Key'],
              startsWith('mobile-learning-path-adapt-path-1-'),
            );
            return jsonResponse({
              'id': 'adapt-job-1',
              'operation': 'adapt',
              'status': 'queued',
              'learning_path_id': 'path-1',
            }, 202);
          }
          if (request.url.path == '/api/v1/learning-path-jobs/adapt-job-1') {
            return jsonResponse({
              'id': 'adapt-job-1',
              'operation': 'adapt',
              'status': 'succeeded',
              'learning_path_id': 'path-1',
            }, 200);
          }
          return jsonResponse({
            'id': 'path-1',
            'plan': <String, dynamic>{},
          }, 200);
        }),
      )..accessToken = 'learner-token';

      final response = await client.adaptLearningPath(
        'path-1',
        onStatus: statuses.add,
      );

      expect(requests.map((request) => request.url.path), [
        '/api/v1/learning-path-jobs/path-1/adapt',
        '/api/v1/learning-path-jobs/adapt-job-1',
        '/api/v1/learning-paths/path-1',
      ]);
      expect(statuses, ['queued', 'succeeded']);
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

  test(
    'teacher application endpoints use the learner review contract',
    () async {
      final requests = <http.Request>[];
      final client = ApiClient(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'GET') {
            return jsonResponse({'application': null});
          }
          return jsonResponse({
            'id': 'application-1',
            'user_id': 'learner-1',
            'motivation': 'I have taught English for several years.',
            'organization': 'Community Center',
            'status': 'pending',
            'review_note': null,
            'requested_at': '2026-07-22T00:00:00Z',
            'reviewed_at': null,
          }, 201);
        }),
      )..accessToken = 'learner-token';

      final current = await client.teacherApplication();
      final submitted = await client.submitTeacherApplication(
        motivation: 'I have taught English for several years.',
        organization: 'Community Center',
      );

      expect(current['application'], isNull);
      expect(requests[0].url.path, '/api/v1/teacher-applications/me');
      expect(requests[1].url.path, '/api/v1/teacher-applications');
      expect(requests[1].headers['Authorization'], 'Bearer learner-token');
      expect(jsonDecode(requests[1].body), {
        'motivation': 'I have taught English for several years.',
        'organization': 'Community Center',
      });
      expect(submitted['status'], 'pending');
    },
  );

  test('class APIs accept bare lists and submit learner text', () async {
    final requests = <http.Request>[];
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        requests.add(request);
        if (request.method == 'GET' && request.url.path == '/api/v1/classes') {
          return http.Response(
            jsonEncode([
              {'id': 'class-1', 'name': 'IELTS 01'},
            ]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (request.method == 'POST') {
          return jsonResponse({'id': 'grading-job-1', 'status': 'queued'}, 202);
        }
        if (request.url.path ==
            '/api/v1/assignment-grading-jobs/grading-job-1') {
          return jsonResponse({
            'id': 'grading-job-1',
            'status': 'succeeded',
            'analysis_id': 'analysis-1',
          });
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
    final submitRequest = requests.firstWhere(
      (request) => request.method == 'POST',
    );
    expect(submitRequest.url.path, '/api/v1/assignments/assignment-1/submit');
    expect(jsonDecode(submitRequest.body), {'input_text': 'My answer'});
    expect(
      submitRequest.headers['Idempotency-Key'],
      startsWith('mobile-assignment-'),
    );
    expect(submission['status'], 'submitted');
  });

  test('contextual analysis includes learning path and task day', () async {
    late http.Request capturedPost;
    final client = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'POST') {
          capturedPost = request;
          return jsonResponse({'id': 'job-1', 'status': 'queued'}, 202);
        }
        if (request.url.path == '/api/v1/analysis-jobs/job-1') {
          return jsonResponse({
            'id': 'job-1',
            'status': 'succeeded',
            'analysis_id': 'analysis-1',
          });
        }
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
      lessonId: 'lesson-1',
    );

    expect(capturedPost.url.path, '/api/v1/analysis-jobs/writing');
    expect(capturedPost.headers['Idempotency-Key'], startsWith('mobile-'));
    expect(jsonDecode(capturedPost.body), {
      'input_text': 'My paragraph.',
      'learning_path_id': 'path-1',
      'task_day': 3,
      'lesson_id': 'lesson-1',
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

  test('learning space header scopes curriculum requests', () async {
    late http.Request captured;
    final client =
        ApiClient(
            baseUrl: 'https://api.example.test',
            client: MockClient((request) async {
              captured = request;
              return jsonResponse({
                'items': [
                  {'id': 'course-1', 'code': 'ielts-band-5-6'},
                ],
              });
            }),
          )
          ..accessToken = 'learner-token'
          ..learningSpaceId = 'self-space-1';

    final courses = await client.courses(kind: 'ielts');

    expect(captured.url.path, '/api/v1/content/courses');
    expect(captured.url.queryParameters['kind'], 'ielts');
    expect(captured.headers['Authorization'], 'Bearer learner-token');
    expect(captured.headers['X-Learning-Space-ID'], 'self-space-1');
    expect(courses.single['code'], 'ielts-band-5-6');
  });

  test(
    'lesson media progress includes the active lesson and media ids',
    () async {
      late http.Request captured;
      final client =
          ApiClient(
              baseUrl: 'https://api.example.test',
              client: MockClient((request) async {
                captured = request;
                return jsonResponse({
                  'media_progress': {
                    'media-1': {'position_seconds': 12},
                  },
                });
              }),
            )
            ..accessToken = 'learner-token'
            ..learningSpaceId = 'self-space-1';

      await client.updateLessonMediaProgress(
        lessonId: 'lesson-1',
        mediaId: 'media-1',
        positionSeconds: 12,
        completed: false,
      );

      expect(captured.method, 'PATCH');
      expect(
        captured.url.path,
        '/api/v1/content/lessons/lesson-1/media-progress',
      );
      expect(captured.headers['Authorization'], 'Bearer learner-token');
      expect(captured.headers['X-Learning-Space-ID'], 'self-space-1');
      expect(jsonDecode(captured.body), {
        'media_id': 'media-1',
        'position_seconds': 12,
        'completed': false,
      });
    },
  );

  test('relative lesson media URLs resolve against the API base URL', () {
    final client = ApiClient(baseUrl: 'https://api.example.test');

    expect(
      client.resolveMediaUrl('/api/v1/content/media/media-1/stream'),
      'https://api.example.test/api/v1/content/media/media-1/stream',
    );
    expect(
      client.resolveMediaUrl('https://cdn.example.test/audio.mp3'),
      'https://cdn.example.test/audio.mp3',
    );
  });
}

http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
