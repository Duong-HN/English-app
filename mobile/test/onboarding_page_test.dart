import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/core/auth_controller.dart';
import 'package:english_ai_tutor/src/core/token_store.dart';
import 'package:english_ai_tutor/src/features/onboarding/onboarding_page.dart';

void main() {
  testWidgets('placement test shows one question at a time then builds path', (
    tester,
  ) async {
    var placementSubmitted = false;
    var onboardingCompleted = false;
    var completed = false;
    final questions = List.generate(
      20,
      (index) => {
        'id': 'q${index + 1}',
        'prompt': 'Question ${index + 1}',
        'skill': index.isEven ? 'grammar' : 'vocabulary',
        'options': ['Answer A', 'Answer B', 'Answer C', 'Answer D'],
      },
    );
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/onboarding') {
          return jsonResponse(
                onboardingCompleted
                ? {
                    'status': 'completed',
                    'goal': 'ielts',
                    'daily_minutes': 30,
                    'learning_path': {'id': 'path-1'},
                  }
                : placementSubmitted
                ? {
                    'status': 'needs_learning_path',
                    'goal': 'ielts',
                    'daily_minutes': 30,
                    'placement_result': {
                      'score': 14,
                      'total_questions': 20,
                      'level': 'B1',
                      'skill_scores': {'grammar': 7, 'vocabulary': 7},
                    },
                  }
                : {
                    'status': 'needs_placement',
                    'goal': 'ielts',
                    'daily_minutes': 30,
                  },
          );
        }
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/placement-test') {
          return jsonResponse({'questions': questions, 'total_questions': 20});
        }
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/placement-test/submit') {
          final answers =
              (jsonDecode(request.body) as Map<String, dynamic>)['answers']
                  as Map<String, dynamic>;
          expect(answers, hasLength(20));
          placementSubmitted = true;
          return jsonResponse({
            'score': 14,
            'total_questions': 20,
            'level': 'B1',
            'skill_scores': {'grammar': 7, 'vocabulary': 7},
          }, 201);
        }
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/onboarding/complete') {
          onboardingCompleted = true;
          return jsonResponse({
            'id': 'onboarding-job-1',
            'operation': 'onboarding',
            'status': 'queued',
            'learning_path_id': null,
          }, 202);
        }
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/learning-path-jobs/onboarding-job-1') {
          return jsonResponse({
            'id': 'onboarding-job-1',
            'operation': 'onboarding',
            'status': 'succeeded',
            'learning_path_id': 'path-1',
          });
        }
        return jsonResponse({'detail': 'Unexpected request'}, 500);
      }),
    )..accessToken = 'learner-token';
    final authController = AuthController(
      apiClient: apiClient,
      tokenStore: MemoryTokenStore(),
    )..user = {'id': 'learner-1', 'role': 'learner', 'display_name': 'Learner'};

    await tester.pumpWidget(
      MaterialApp(
        home: OnboardingPage(
          apiClient: apiClient,
          authController: authController,
          onCompleted: () => completed = true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Question 1'), findsOneWidget);
    expect(find.text('Question 2'), findsNothing);
    for (var number = 1; number <= 20; number++) {
      final answer = find.byKey(Key('answer-q$number-a'));
      await tester.ensureVisible(answer);
      await tester.tap(answer);
      await tester.pump();
      final next = find.byKey(const Key('placement-next'));
      await tester.ensureVisible(next);
      await tester.tap(next);
      await tester.pumpAndSettle();
    }

    expect(find.text('B1'), findsOneWidget);
    expect(find.text('14/20 câu đúng'), findsOneWidget);
    await tester.tap(find.byKey(const Key('generate-onboarding-path')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(completed, isTrue);
    authController.dispose();
  });
}

http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
