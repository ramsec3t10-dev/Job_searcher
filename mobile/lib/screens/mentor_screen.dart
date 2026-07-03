import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../services/tools_service.dart';
import '../theme/app_theme.dart';

class _Msg {
  _Msg(this.role, this.text);
  final String role; // 'user' | 'assistant'
  final String text;
}

/// Module 15 — AI Career Mentor chat.
class MentorScreen extends StatefulWidget {
  const MentorScreen({super.key});

  @override
  State<MentorScreen> createState() => _MentorScreenState();
}

class _MentorScreenState extends State<MentorScreen> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  final List<_Msg> _messages = [
    _Msg('assistant',
        'Hi! I\'m your AI Career Mentor. Ask me about skills, interviews, salary, or which companies to target.'),
  ];
  bool _sending = false;

  static const _suggestions = [
    'How do I get into Qualcomm?',
    'Am I underpaid?',
    'What should I learn next?',
    'How do I prepare for interviews?',
  ];

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _controller.text).trim();
    if (text.isEmpty || _sending) return;
    _controller.clear();
    setState(() {
      _messages.add(_Msg('user', text));
      _sending = true;
    });
    _scrollToEnd();

    final history = _messages
        .where((m) => m != _messages.last)
        .map((m) => {'role': m.role, 'content': m.text})
        .toList();

    try {
      final res =
          await context.read<ToolsService>().mentorChat(text, history: history);
      final reply = (res['reply'] as String?)?.trim();
      setState(() => _messages
          .add(_Msg('assistant', reply?.isNotEmpty == true ? reply! : '…')));
    } on ApiException catch (e) {
      setState(() => _messages.add(_Msg('assistant', 'Sorry — ${e.message}')));
    } catch (_) {
      setState(() =>
          _messages.add(_Msg('assistant', 'Could not reach the mentor. Try again.')));
    } finally {
      setState(() => _sending = false);
      _scrollToEnd();
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('AI Mentor',
            style: TextStyle(fontWeight: FontWeight.w700)),
        titleSpacing: AppSpacing.md,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.all(AppSpacing.md),
                itemCount: _messages.length + (_sending ? 1 : 0),
                itemBuilder: (context, i) {
                  if (i == _messages.length) return const _TypingBubble();
                  return _Bubble(msg: _messages[i]);
                },
              ),
            ),
            if (_messages.length <= 1) _suggestionChips(),
            _composer(),
          ],
        ),
      ),
    );
  }

  Widget _suggestionChips() {
    return Container(
      alignment: Alignment.centerLeft,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      height: 48,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _suggestions.length,
        separatorBuilder: (_, __) => const SizedBox(width: AppSpacing.sm),
        itemBuilder: (context, i) => ActionChip(
          label: Text(_suggestions[i]),
          labelStyle: const TextStyle(color: AppTheme.brand, fontSize: 12),
          backgroundColor: AppTheme.card,
          side: const BorderSide(color: AppTheme.divider),
          onPressed: () => _send(_suggestions[i]),
        ),
      ),
    );
  }

  Widget _composer() {
    return Container(
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.md),
      decoration: const BoxDecoration(
        color: AppTheme.card,
        border: Border(top: BorderSide(color: AppTheme.divider)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _send(),
              decoration: const InputDecoration(
                hintText: 'Ask your mentor…',
                contentPadding: EdgeInsets.symmetric(
                    horizontal: AppSpacing.md, vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          _SendButton(enabled: !_sending, onTap: _send),
        ],
      ),
    );
  }
}

class _SendButton extends StatelessWidget {
  const _SendButton({required this.enabled, required this.onTap});
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: enabled ? AppTheme.brand : AppTheme.textMuted,
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: enabled ? onTap : null,
        child: const Padding(
          padding: EdgeInsets.all(12),
          child: Icon(Icons.send_rounded, color: Colors.white, size: 20),
        ),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.msg});
  final _Msg msg;

  @override
  Widget build(BuildContext context) {
    final isUser = msg.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.78),
        margin: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md, vertical: 10),
        decoration: BoxDecoration(
          color: isUser ? AppTheme.brand : AppTheme.card,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          border: isUser ? null : Border.all(color: AppTheme.divider),
        ),
        child: Text(
          msg.text,
          style: AppText.body.copyWith(
            color: isUser ? Colors.white : AppTheme.textPrimary,
          ),
        ),
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md, vertical: 14),
        decoration: BoxDecoration(
          color: AppTheme.card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.divider),
        ),
        child: const SizedBox(
          width: 36,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Dot(), _Dot(), _Dot(),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot();
  @override
  Widget build(BuildContext context) => Container(
        width: 7,
        height: 7,
        decoration: const BoxDecoration(
            color: AppTheme.textMuted, shape: BoxShape.circle),
      );
}
