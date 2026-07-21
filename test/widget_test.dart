import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:english_ai_tutor/src/app.dart';
import 'package:english_ai_tutor/src/core/token_store.dart';

void main() {
  testWidgets('unauthenticated user sees the login form', (tester) async {
    await tester.pumpWidget(LearnMateApp(tokenStore: MemoryTokenStore()));
    await tester.pumpAndSettle();

    expect(find.byType(TextFormField), findsNWidgets(2));
    expect(find.byType(FilledButton), findsOneWidget);
    expect(find.byIcon(Icons.login), findsOneWidget);
  });
}
