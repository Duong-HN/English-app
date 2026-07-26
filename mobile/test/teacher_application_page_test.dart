import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/features/teacher/teacher_application_page.dart';

void main() {
  testWidgets(
    'learner can submit a teacher application and see pending state',
    (tester) async {
      final client = ApiClient(
        baseUrl: 'https://api.example.test',
        client: MockClient((request) async {
          if (request.method == 'GET') {
            return _jsonResponse({'application': null});
          }
          return _jsonResponse({
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

      await tester.pumpWidget(
        MaterialApp(home: TeacherApplicationPage(apiClient: client)),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('teacher-application-form')), findsOneWidget);
      expect(find.byKey(const Key('teacher-motivation')), findsOneWidget);
      await tester.enterText(
        find.byKey(const Key('teacher-motivation')),
        'I have taught English for several years.',
      );
      await tester.enterText(
        find.byKey(const Key('teacher-organization')),
        'Community Center',
      );
      await tester.tap(find.byKey(const Key('submit-teacher-application')));
      await tester.pumpAndSettle();

      expect(find.text('Hồ sơ đang chờ duyệt'), findsOneWidget);
      expect(find.byKey(const Key('submit-teacher-application')), findsNothing);
    },
  );
}

http.Response _jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
