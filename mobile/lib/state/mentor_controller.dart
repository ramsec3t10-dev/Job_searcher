import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/eh_api_client.dart';
import 'core_providers.dart';

enum MentorRole { user, assistant }

/// A single message in the career-mentor conversation.
class MentorMessage {
  const MentorMessage({
    required this.role,
    required this.text,
    this.pending = false,
  });

  final MentorRole role;
  final String text;

  /// True while an assistant reply is streaming / being awaited.
  final bool pending;

  MentorMessage copyWith({String? text, bool? pending}) => MentorMessage(
        role: role,
        text: text ?? this.text,
        pending: pending ?? this.pending,
      );
}

/// Immutable view of the mentor conversation.
class MentorState {
  const MentorState({this.messages = const [], this.sending = false});
  final List<MentorMessage> messages;
  final bool sending;

  MentorState copyWith({List<MentorMessage>? messages, bool? sending}) =>
      MentorState(
        messages: messages ?? this.messages,
        sending: sending ?? this.sending,
      );
}

/// Career-mentor chat controller. Optimistically appends the user's message and
/// a pending assistant bubble, then resolves it with the API response.
class MentorController extends Notifier<MentorState> {
  EHApiClient get _api => ref.read(apiClientProvider);

  @override
  MentorState build() => const MentorState();

  Future<void> send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || state.sending) return;

    final withUser = [
      ...state.messages,
      MentorMessage(role: MentorRole.user, text: trimmed),
      const MentorMessage(role: MentorRole.assistant, text: '', pending: true),
    ];
    state = state.copyWith(messages: withUser, sending: true);

    try {
      final data = await _api
          .post('/mentor/chat', body: {'message': trimmed}) as Map<String, dynamic>;
      final reply = (data['reply'] ?? data['message'] ?? data['response'] ?? '')
          .toString();
      _resolveLast(reply.isEmpty ? 'No response.' : reply);
    } on EHApiException catch (e) {
      _resolveLast(e.message);
    } catch (_) {
      _resolveLast('Something went wrong. Please try again.');
    } finally {
      state = state.copyWith(sending: false);
    }
  }

  void clear() => state = const MentorState();

  void _resolveLast(String text) {
    final messages = [...state.messages];
    final idx = messages.lastIndexWhere((m) => m.pending);
    if (idx == -1) {
      messages.add(MentorMessage(role: MentorRole.assistant, text: text));
    } else {
      messages[idx] = messages[idx].copyWith(text: text, pending: false);
    }
    state = state.copyWith(messages: messages);
  }
}

final mentorControllerProvider =
    NotifierProvider<MentorController, MentorState>(MentorController.new);
