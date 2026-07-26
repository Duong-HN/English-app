import 'dart:async';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

import '../../core/api_client.dart';

typedef AudioPlayback = Future<void> Function(String url);

class VocabularyDetailPage extends StatefulWidget {
  const VocabularyDetailPage({
    super.key,
    required this.apiClient,
    required this.word,
    this.audioPlayback,
  });

  final ApiClient apiClient;
  final String word;
  final AudioPlayback? audioPlayback;

  @override
  State<VocabularyDetailPage> createState() => _VocabularyDetailPageState();
}

class _VocabularyDetailPageState extends State<VocabularyDetailPage> {
  AudioPlayer? _audioPlayer;
  Map<String, dynamic>? _lookup;
  String? _error;
  String? _loadingAudioUrl;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant VocabularyDetailPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.word != widget.word ||
        oldWidget.apiClient != widget.apiClient) {
      _load();
    }
  }

  @override
  void dispose() {
    final player = _audioPlayer;
    if (player != null) unawaited(player.dispose());
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _lookup = null;
      _error = null;
    });
    try {
      final lookup = await widget.apiClient.lookupWord(widget.word);
      if (mounted) setState(() => _lookup = lookup);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Không thể kết nối máy chủ.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _playAudio(String url) async {
    setState(() {
      _loadingAudioUrl = url;
      _error = null;
    });
    try {
      final playback = widget.audioPlayback;
      if (playback != null) {
        await playback(url);
      } else {
        final player = _audioPlayer ??= AudioPlayer();
        await player.stop();
        await player.setUrl(url);
        unawaited(player.play());
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Không thể phát audio lúc này.')),
      );
    } finally {
      if (mounted) setState(() => _loadingAudioUrl = null);
    }
  }

  List<Map<String, dynamic>> _maps(String key) {
    return (_lookup?[key] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  List<String> _strings(String key) {
    return (_lookup?[key] as List<dynamic>? ?? const [])
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }

  bool get _isEmpty {
    return _maps('phonetics').isEmpty &&
        _maps('meanings').isEmpty &&
        _strings('synonyms').isEmpty &&
        _strings('antonyms').isEmpty &&
        _strings('collocations').isEmpty;
  }

  @override
  Widget build(BuildContext context) {
    final title = _lookup?['word']?.toString() ?? widget.word.trim();
    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiết từ vựng')),
      body: SafeArea(
        child: switch ((_loading, _error, _lookup)) {
          (true, _, _) => const Center(
            key: Key('word-lookup-loading'),
            child: CircularProgressIndicator(),
          ),
          (false, final error?, _) => _LookupMessage(
            key: const Key('word-lookup-error'),
            icon: Icons.cloud_off_outlined,
            title: 'Không thể tra từ',
            message: error,
            onRetry: _load,
          ),
          (false, null, Map<String, dynamic>()) when _isEmpty => _LookupMessage(
            key: const Key('word-lookup-empty'),
            icon: Icons.menu_book_outlined,
            title: 'Chưa tìm thấy “$title”',
            message: 'Hãy kiểm tra chính tả hoặc thử lại sau.',
            onRetry: _load,
          ),
          (false, null, _) => RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              key: const Key('word-lookup-content'),
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              children: [
                _buildWordHeader(context, title),
                ..._buildMeanings(context),
                _buildWordGroup(
                  context,
                  title: 'Từ đồng nghĩa',
                  words: _strings('synonyms'),
                ),
                _buildWordGroup(
                  context,
                  title: 'Từ trái nghĩa',
                  words: _strings('antonyms'),
                ),
                _buildWordGroup(
                  context,
                  title: 'Collocation (từ đi cùng)',
                  words: _strings('collocations'),
                  keyPrefix: 'collocation',
                ),
              ],
            ),
          ),
        },
      ),
    );
  }

  Widget _buildWordHeader(BuildContext context, String title) {
    final phonetics = _maps('phonetics');
    final ipa = phonetics
        .map((item) => item['text']?.toString().trim())
        .whereType<String>()
        .where((item) => item.isNotEmpty)
        .toSet()
        .toList();
    final audioUrl = phonetics
        .map((item) => item['audio_url']?.toString().trim())
        .whereType<String>()
        .where((item) => item.isNotEmpty)
        .firstOrNull;

    return Card(
      margin: const EdgeInsets.only(bottom: 18),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  if (ipa.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      ipa.join('  •  '),
                      key: const Key('word-phonetics'),
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (audioUrl != null) ...[
              const SizedBox(width: 12),
              IconButton.filledTonal(
                key: const Key('play-pronunciation'),
                tooltip: 'Nghe phát âm',
                onPressed: _loadingAudioUrl == null
                    ? () => _playAudio(audioUrl)
                    : null,
                icon: _loadingAudioUrl == audioUrl
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.volume_up_outlined),
              ),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _buildMeanings(BuildContext context) {
    final meanings = _maps('meanings');
    if (meanings.isEmpty) return const [];
    return [
      Text('Nghĩa của từ', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 8),
      ...meanings.asMap().entries.map((entry) {
        final meaning = entry.value;
        final partOfSpeech = meaning['part_of_speech']?.toString().trim() ?? '';
        final definitions = _nestedStrings(meaning, 'definitions');
        final examples = _nestedStrings(meaning, 'examples');
        return Card(
          key: Key('word-meaning-${entry.key}'),
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (partOfSpeech.isNotEmpty)
                  Text(
                    partOfSpeech,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ...definitions.asMap().entries.map(
                  (definition) => Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${definition.key + 1}. '),
                        Expanded(child: Text(definition.value)),
                      ],
                    ),
                  ),
                ),
                if (examples.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text('Ví dụ', style: Theme.of(context).textTheme.titleSmall),
                  ...examples.map(
                    (example) => Padding(
                      padding: const EdgeInsets.only(top: 5),
                      child: Text(
                        '“$example”',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      }),
      const SizedBox(height: 4),
    ];
  }

  Widget _buildWordGroup(
    BuildContext context, {
    required String title,
    required List<String> words,
    String? keyPrefix,
  }) {
    if (words.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: words
                .map(
                  (word) => Chip(
                    key: keyPrefix == null ? null : Key('$keyPrefix-$word'),
                    label: Text(word),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }

  List<String> _nestedStrings(Map<String, dynamic> value, String key) {
    return (value[key] as List<dynamic>? ?? const [])
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }
}

class _LookupMessage extends StatelessWidget {
  const _LookupMessage({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    required this.onRetry,
  });

  final IconData icon;
  final String title;
  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 56, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 18),
            OutlinedButton.icon(
              key: const Key('retry-word-lookup'),
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Thử lại'),
            ),
          ],
        ),
      ),
    );
  }
}
