import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/features/classes/classes_page.dart';

void main() {
  testWidgets('reopening an assignment restores submission and feedback', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.url.path, '/api/v1/assignments/assignment-1/submission');
        return jsonResponse({
          'id': 'submission-1',
          'assignment_id': 'assignment-1',
          'status': 'reviewed',
          'input_text': 'My previously submitted paragraph.',
          'analysis': {
            'score': 9,
            'result': {'summary': 'Strong structure and vocabulary.'},
          },
          'teacher_feedback': 'Excellent improvement.',
        });
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(
      MaterialApp(
        home: AssignmentSubmissionPage(
          apiClient: apiClient,
          assignment: const {
            'id': 'assignment-1',
            'title': 'Write a paragraph',
            'content': 'Describe your hometown.',
            'submission_id': 'submission-1',
            'submission_status': 'reviewed',
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key('assignment-input')),
    );
    expect(field.controller?.text, 'My previously submitted paragraph.');
    expect(find.text('Điểm tham khảo: 9/10'), findsOneWidget);
    expect(find.text('Strong structure and vocabulary.'), findsOneWidget);
    expect(find.text('Excellent improvement.'), findsOneWidget);
  });

  testWidgets('learner joins a class, opens an assignment and submits work', (
    tester,
  ) async {
    var joined = false;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'GET' && request.url.path == '/api/v1/classes') {
          return jsonResponse({
            'items': joined
                ? [
                    {
                      'id': 'class-1',
                      'name': 'IELTS 01',
                      'teacher_name': 'Cô Linh',
                      'member_count': 12,
                    },
                  ]
                : <Map<String, dynamic>>[],
            'total': joined ? 1 : 0,
          });
        }
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/classes/join') {
          expect(jsonDecode(request.body), {'invite_code': 'IELTS001'});
          joined = true;
          return jsonResponse({
            'id': 'class-1',
            'name': 'IELTS 01',
            'teacher_name': 'Cô Linh',
          });
        }
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/classes/class-1/assignments') {
          return jsonResponse({
            'items': [
              {
                'id': 'assignment-1',
                'title': 'Write about your hometown',
                'skill': 'writing',
                'content': 'Write at least one short paragraph.',
                'estimated_minutes': 20,
                'due_at': '2026-08-01T12:00:00Z',
              },
            ],
            'total': 1,
          });
        }
        if (request.method == 'GET' &&
            request.url.path ==
                '/api/v1/assignment-grading-jobs/grading-job-1') {
          return jsonResponse({
            'id': 'grading-job-1',
            'status': 'succeeded',
            'analysis_id': 'analysis-1',
          });
        }
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/assignments/assignment-1/submission') {
          return jsonResponse({
            'id': 'submission-1',
            'status': 'submitted',
            'analysis': {
              'score': 8,
              'result': {'summary': 'A clear and relevant paragraph.'},
            },
          });
        }
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/assignments/assignment-1/submit') {
          expect(
            (jsonDecode(request.body) as Map<String, dynamic>)['input_text'],
            'My hometown is peaceful and friendly.',
          );
          return jsonResponse({'id': 'grading-job-1', 'status': 'queued'}, 202);
        }
        return jsonResponse({'detail': 'Unexpected request'}, 500);
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(
      MaterialApp(home: ClassesPage(apiClient: apiClient)),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('class-invite-code')),
      'IELTS001',
    );
    await tester.tap(find.byKey(const Key('join-class')));
    await tester.pumpAndSettle();
    expect(find.text('IELTS 01'), findsOneWidget);

    await tester.tap(find.text('IELTS 01'));
    await tester.pumpAndSettle();
    expect(find.text('Write about your hometown'), findsOneWidget);

    await tester.tap(find.text('Write about your hometown'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('assignment-input')),
      'My hometown is peaceful and friendly.',
    );
    await tester.tap(find.byKey(const Key('submit-assignment')));
    await tester.pumpAndSettle();

    expect(find.text('Điểm tham khảo: 8/10'), findsOneWidget);
    expect(find.text('A clear and relevant paragraph.'), findsOneWidget);
  });
}

http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
