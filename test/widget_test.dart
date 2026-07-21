import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:english_ai_tutor/src/app.dart';

void main() {
  testWidgets('home page renders the learning assistant', (tester) async {
    await tester.pumpWidget(const LearnMateApp());

    expect(find.byType(TextField), findsOneWidget);
    expect(find.byType(FilledButton), findsOneWidget);
  });
}
