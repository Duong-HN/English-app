import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/features/classes/classes_page.dart';

http.Response jsonResponse(Object body, int status) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);

Map<String, dynamic> classroom({
  String status = 'active',
  bool isActive = true,
}) => {
  'id': 'class-1',
  'teacher_id': 'teacher-1',
  'teacher_display_name': 'Cô An',
  'teacher_email': 'teacher@example.com',
  'name': 'Lớp giao tiếp B1',
  'description': 'Luyện tiếng Anh cho công việc.',
  'target_level': 'B1',
  'is_active': isActive,
  'membership_status': status,
  'created_at': '2026-07-22T00:00:00Z',
  'updated_at': '2026-07-22T00:00:00Z',
};

Map<String, dynamic> assignment({
  String id = 'assignment-1',
  String skill = 'writing',
  int submissionCount = 0,
  String status = 'published',
  String dueAt = '2099-08-01T12:00:00Z',
}) => {
  'id': id,
  'class_id': 'class-1',
  'class_name': 'Lớp giao tiếp B1',
  'created_by_id': 'teacher-1',
  'created_by_display_name': 'Cô An',
  'title': 'Bài luyện $skill',
  'instructions': 'Hoàn thành một bài phân tích phù hợp.',
  'skill_type': skill,
  'target_level': 'B1',
  'due_at': dueAt,
  'status': status,
  'submission_count': submissionCount,
  'my_submission_count': submissionCount,
  'created_at': '2026-07-22T00:00:00Z',
  'updated_at': '2026-07-22T00:00:00Z',
};

Widget testApp(ApiClient apiClient, {bool isLearner = true}) {
  return MaterialApp(
    home: Scaffold(
      body: ClassesPage(apiClient: apiClient, isLearner: isLearner),
    ),
  );
}

void main() {
  testWidgets(
    'join code is validated, normalized and shows pending membership',
    (tester) async {
      var joined = false;
      String? submittedCode;
      final apiClient = ApiClient(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          if (request.method == 'GET' &&
              request.url.path == '/api/v1/classes/mine') {
            return jsonResponse({
              'items': joined ? [classroom(status: 'pending')] : [],
              'total': joined ? 1 : 0,
            }, 200);
          }
          expect(request.method, 'POST');
          expect(request.url.path, '/api/v1/classes/join');
          submittedCode = jsonDecode(request.body)['join_code'] as String;
          joined = true;
          return jsonResponse(classroom(status: 'pending'), 201);
        }),
      )..accessToken = 'learner-token';

      await tester.pumpWidget(testApp(apiClient));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('join-class')));
      await tester.pump();
      expect(find.text('Hãy nhập mã tham gia lớp'), findsOneWidget);

      await tester.enterText(find.byKey(const Key('class-join-code')), 'ABC');
      await tester.tap(find.byKey(const Key('join-class')));
      await tester.pump();
      expect(
        find.text('Mã tham gia phải có từ 6 đến 16 ký tự'),
        findsOneWidget,
      );

      await tester.enterText(
        find.byKey(const Key('class-join-code')),
        '  abC123  ',
      );
      await tester.tap(find.byKey(const Key('join-class')));
      await tester.pumpAndSettle();

      expect(submittedCode, 'ABC123');
      expect(find.text('Đang chờ duyệt'), findsWidgets);
      expect(find.text('Lớp giao tiếp B1'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('pending-class-class-1')),
        findsOneWidget,
      );
    },
  );

  testWidgets('inactive class is shown as paused without loading assignments', (
    tester,
  ) async {
    var assignmentRequestCount = 0;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/classes/mine') {
          return jsonResponse({
            'items': [classroom(isActive: false)],
            'total': 1,
          }, 200);
        }
        assignmentRequestCount++;
        return jsonResponse({'items': [], 'total': 0}, 200);
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(testApp(apiClient));
    await tester.pumpAndSettle();

    expect(find.text('Lớp tạm dừng'), findsOneWidget);
    expect(find.byKey(const ValueKey('paused-class-class-1')), findsOneWidget);
    expect(find.byKey(const Key('selected-class-detail')), findsNothing);
    expect(assignmentRequestCount, 0);
  });

  testWidgets('learner selects a matching recent analysis and submits it', (
    tester,
  ) async {
    var submissions = 0;
    String? submittedAnalysisId;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/classes/mine') {
          return jsonResponse({
            'items': [classroom()],
            'total': 1,
          }, 200);
        }
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/classes/class-1/assignments') {
          return jsonResponse({
            'items': [assignment(submissionCount: submissions)],
            'total': 1,
          }, 200);
        }
        if (request.method == 'GET' && request.url.path == '/api/v1/analyses') {
          return jsonResponse({
            'items': [
              {
                'id': 'reading-1',
                'type': 'reading',
                'input_text': 'Reading sample',
                'created_at': '2026-07-20T00:00:00Z',
              },
              {
                'id': 'writing-1',
                'type': 'writing',
                'input_text': 'Writing answer for the assignment',
                'score': 8,
                'created_at': '2026-07-21T00:00:00Z',
              },
            ],
            'total': 2,
          }, 200);
        }
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/api/v1/assignments/assignment-1/submissions',
        );
        submittedAnalysisId = jsonDecode(request.body)['analysis_id'] as String;
        submissions++;
        return jsonResponse({
          'id': 'submission-1',
          'assignment_id': 'assignment-1',
          'analysis_id': submittedAnalysisId,
          'attempt_number': submissions,
        }, 201);
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(testApp(apiClient));
    await tester.pumpAndSettle();
    final submitButton = find.byKey(
      const ValueKey('submit-assignment-assignment-1'),
    );
    await tester.scrollUntilVisible(
      submitButton,
      400,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(submitButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Writing answer for the assignment'), findsOneWidget);
    expect(find.text('Reading sample'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('analysis-choice-writing-1')));
    await tester.pumpAndSettle();

    expect(submittedAnalysisId, 'writing-1');
    expect(find.text('Bạn đã nộp 1 lần.'), findsOneWidget);
  });

  testWidgets('assignment explains when no recent analysis matches its skill', (
    tester,
  ) async {
    var submissionCalled = false;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/classes/mine') {
          return jsonResponse({
            'items': [classroom()],
            'total': 1,
          }, 200);
        }
        if (request.url.path.endsWith('/assignments')) {
          return jsonResponse({
            'items': [assignment(skill: 'speaking')],
            'total': 1,
          }, 200);
        }
        if (request.url.path == '/api/v1/analyses') {
          return jsonResponse({
            'items': [
              {
                'id': 'writing-1',
                'type': 'writing',
                'input_text': 'A writing answer',
              },
            ],
            'total': 1,
          }, 200);
        }
        submissionCalled = true;
        return jsonResponse({'id': 'unexpected'}, 201);
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(testApp(apiClient));
    await tester.pumpAndSettle();
    final submitButton = find.byKey(
      const ValueKey('submit-assignment-assignment-1'),
    );
    await tester.scrollUntilVisible(
      submitButton,
      400,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(submitButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Chưa có bài phân tích phù hợp'), findsOneWidget);
    expect(find.textContaining('hoàn thành một bài nói'), findsOneWidget);
    await tester.tap(find.text('Đã hiểu'));
    await tester.pumpAndSettle();
    expect(submissionCalled, isFalse);
  });

  testWidgets('closed and overdue assignments cannot be submitted', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/classes/mine') {
          return jsonResponse({
            'items': [classroom()],
            'total': 1,
          }, 200);
        }
        if (request.url.path.endsWith('/assignments')) {
          return jsonResponse({
            'items': [
              assignment(
                id: 'closed-assignment',
                status: 'closed',
                dueAt: '2099-08-01T12:00:00Z',
              ),
              assignment(
                id: 'overdue-assignment',
                dueAt: '2020-08-01T12:00:00Z',
              ),
            ],
            'total': 2,
          }, 200);
        }
        fail('A disabled assignment must not load history or submit.');
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(testApp(apiClient));
    await tester.pumpAndSettle();

    final closedButton = tester.widget<FilledButton>(
      find.byKey(const ValueKey('submit-assignment-closed-assignment')),
    );
    final overdueButton = tester.widget<FilledButton>(
      find.byKey(const ValueKey('submit-assignment-overdue-assignment')),
    );
    expect(closedButton.onPressed, isNull);
    expect(overdueButton.onPressed, isNull);
    expect(find.text('Bài đã đóng'), findsOneWidget);
    expect(find.text('Đã quá hạn'), findsOneWidget);
  });

  testWidgets('active learner confirms leaving a class', (tester) async {
    var active = true;
    var deleteCalled = false;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        if (request.method == 'GET' &&
            request.url.path == '/api/v1/classes/mine') {
          return jsonResponse({
            'items': active ? [classroom()] : [],
            'total': active ? 1 : 0,
          }, 200);
        }
        if (request.method == 'GET') {
          return jsonResponse({'items': [], 'total': 0}, 200);
        }
        expect(request.method, 'DELETE');
        expect(request.url.path, '/api/v1/classes/class-1/membership');
        deleteCalled = true;
        active = false;
        return jsonResponse({'message': 'Membership deleted'}, 200);
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(testApp(apiClient));
    await tester.pumpAndSettle();
    final leaveButton = find.byKey(const ValueKey('leave-class-class-1'));
    await tester.ensureVisible(leaveButton);
    await tester.tap(leaveButton);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('confirm-leave-class')));
    await tester.pumpAndSettle();

    expect(deleteCalled, isTrue);
    expect(
      find.text('Bạn chưa tham gia lớp nào. Nhập mã lớp để bắt đầu.'),
      findsOneWidget,
    );
  });

  testWidgets('non-learner account sees no classroom actions', (tester) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((_) async {
        fail('A non-learner must not call learner classroom endpoints.');
      }),
    )..accessToken = 'teacher-token';

    await tester.pumpWidget(testApp(apiClient, isLearner: false));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('classes-learner-only')), findsOneWidget);
    expect(find.text('Khu vực dành cho học viên'), findsOneWidget);
    expect(find.byKey(const Key('join-class')), findsNothing);
  });
}
