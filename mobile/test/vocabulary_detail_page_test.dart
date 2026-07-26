import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:english_ai_tutor/src/core/api_client.dart';
import 'package:english_ai_tutor/src/features/vocabulary/vocabulary_detail_page.dart';

void main() {
  testWidgets('shows loading then renders dictionary and Datamuse data', (
    tester,
  ) async {
    final response = Completer<http.Response>();
    String? playedUrl;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((request) async {
        expect(request.url.path, '/api/v1/vocabulary/lookup/hello');
        return response.future;
      }),
    )..accessToken = 'learner-token';

    await tester.pumpWidget(
      MaterialApp(
        home: VocabularyDetailPage(
          apiClient: apiClient,
          word: 'hello',
          audioPlayback: (url) async => playedUrl = url,
        ),
      ),
    );
    expect(find.byKey(const Key('word-lookup-loading')), findsOneWidget);

    response.complete(
      jsonResponse({
        'word': 'hello',
        'phonetics': [
          {
            'text': '/həˈləʊ/',
            'audio_url': 'https://audio.example.test/hello.mp3',
          },
        ],
        'meanings': [
          {
            'part_of_speech': 'exclamation',
            'definitions': ['Used as a greeting.'],
            'examples': ['Hello, how are you?'],
          },
        ],
        'synonyms': ['hi'],
        'antonyms': ['goodbye'],
        'collocations': ['say hello', 'hello world'],
        'cached': false,
      }),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('word-lookup-content')), findsOneWidget);
    expect(find.text('hello'), findsOneWidget);
    expect(find.text('/həˈləʊ/'), findsOneWidget);
    expect(find.text('Used as a greeting.'), findsOneWidget);
    expect(find.text('“Hello, how are you?”'), findsOneWidget);
    expect(find.byKey(const Key('collocation-say hello')), findsOneWidget);
    expect(find.byKey(const Key('collocation-hello world')), findsOneWidget);

    await tester.tap(find.byKey(const Key('play-pronunciation')));
    await tester.pumpAndSettle();
    expect(playedUrl, 'https://audio.example.test/hello.mp3');
  });

  testWidgets('shows an empty state when every lookup section is empty', (
    tester,
  ) async {
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient(
        (_) async => jsonResponse({
          'word': 'unknown',
          'phonetics': <Map<String, dynamic>>[],
          'meanings': <Map<String, dynamic>>[],
          'synonyms': <String>[],
          'antonyms': <String>[],
          'collocations': <String>[],
          'cached': false,
        }),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: VocabularyDetailPage(apiClient: apiClient, word: 'unknown'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('word-lookup-empty')), findsOneWidget);
    expect(find.text('Chưa tìm thấy “unknown”'), findsOneWidget);
  });

  testWidgets('shows API errors and lets the learner retry', (tester) async {
    var requestCount = 0;
    final apiClient = ApiClient(
      baseUrl: 'https://api.example.test',
      client: MockClient((_) async {
        requestCount += 1;
        if (requestCount == 1) {
          return jsonResponse({'detail': 'Dictionary is unavailable'}, 503);
        }
        return jsonResponse({
          'word': 'hello',
          'phonetics': <Map<String, dynamic>>[],
          'meanings': <Map<String, dynamic>>[],
          'synonyms': ['hi'],
          'antonyms': <String>[],
          'collocations': <String>[],
          'cached': false,
        });
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: VocabularyDetailPage(apiClient: apiClient, word: 'hello'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('word-lookup-error')), findsOneWidget);
    expect(find.text('Dictionary is unavailable'), findsOneWidget);

    await tester.tap(find.byKey(const Key('retry-word-lookup')));
    await tester.pumpAndSettle();

    expect(requestCount, 2);
    expect(find.byKey(const Key('word-lookup-content')), findsOneWidget);
    expect(find.text('hi'), findsOneWidget);
  });
}

http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);
