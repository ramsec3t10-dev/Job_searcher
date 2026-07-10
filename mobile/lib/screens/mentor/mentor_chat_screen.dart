import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/mentor_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/typography.dart';
import '../../widgets/ai_typing_indicator.dart';
import '../../widgets/empty_state.dart';

class MentorChatScreen extends ConsumerStatefulWidget {
  const MentorChatScreen({super.key});

  @override
  ConsumerState<MentorChatScreen> createState() => _MentorChatScreenState();
}

class _MentorChatScreenState extends ConsumerState<MentorChatScreen> {
  final _input = TextEditingController();

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  void _send() {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    ref.read(mentorControllerProvider.notifier).send(text);
    _input.clear();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(mentorControllerProvider);
    final messages = state.messages;

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                  color: EHColor.success, shape: BoxShape.circle),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('AI Career Mentor',
                      style:
                          EHType.h4.copyWith(color: context.textPrimary)),
                  Text('Knows your profile',
                      style: EHType.caption
                          .copyWith(color: context.textMuted)),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded),
            onPressed: () =>
                ref.read(mentorControllerProvider.notifier).clear(),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: messages.isEmpty
                ? const EHEmptyState(
                    emoji: '💬',
                    title: 'Ask your mentor anything',
                    message:
                        'Career advice, interview prep, salary negotiation — your AI mentor knows your profile.',
                  )
                : ListView.builder(
                    reverse: true,
                    padding: const EdgeInsets.all(16),
                    itemCount: messages.length,
                    itemBuilder: (context, i) {
                      final msg = messages[messages.length - 1 - i];
                      return _Bubble(message: msg);
                    },
                  ),
          ),
          Divider(height: 1, color: context.divider),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
                      style: EHType.bodyMD
                          .copyWith(color: context.textPrimary),
                      decoration: InputDecoration(
                        hintText: 'Ask your mentor anything…',
                        filled: true,
                        fillColor: context.cardElevated,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: state.sending ? null : _send,
                    child: Container(
                      width: 44,
                      height: 44,
                      decoration: const BoxDecoration(
                          color: EHColor.brand, shape: BoxShape.circle),
                      child: const Icon(Icons.send_rounded,
                          color: Colors.white, size: 20),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message});
  final MentorMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == MentorRole.user;
    if (!isUser && message.pending) {
      return const Padding(
        padding: EdgeInsets.only(bottom: 12),
        child: Align(
          alignment: Alignment.centerLeft,
          child: AITypingIndicator(),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                gradient: EHColor.brandGrad,
                borderRadius: BorderRadius.circular(9),
              ),
              child: const Icon(Icons.smart_toy_rounded,
                  color: Colors.white, size: 16),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isUser
                    ? EHColor.brand.withValues(alpha: 0.20)
                    : context.card,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: context.divider),
              ),
              child: Text(message.text,
                  style: EHType.bodySM.copyWith(
                      color: context.textPrimary, height: 1.5)),
            ),
          ),
        ],
      ),
    );
  }
}
