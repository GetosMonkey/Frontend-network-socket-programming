
# Encodes a message into 'SEQ|TYPE|BODY' format followed by a newline.
def encode_packet(sequence_number, message_type, body_text):
    
    packet_str = f"{sequence_number}|{message_type}|{body_text}"
    if not packet_str.endswith('\n'):
        packet_str += '\n'
    return packet_str.encode('utf-8')

# Reads and parses a 'SEQ|TYPE|BODY' message from the socket byte by byte until finding a newline
def receive_packet(sock):
    try:
        data_buffer = b""
        while True:
            char = sock.recv(1)
            if not char:
                return None, None, None # Connection closed
            if char == b'\n':
                break
            data_buffer += char
            
        full_text = data_buffer.decode('utf-8', errors='replace').strip()
        if not full_text:
            return 0, "EMPTY", ""

        parts = full_text.split('|', 2)
        if len(parts) == 3:
            seq = int(parts[0])
            msg_type = parts[1]
            body = parts[2]
            return seq, msg_type, body
        else:
            return 1, "DATA", full_text
    except EOFError:
        return None, None, None
    except Exception:
        # Re-raise to let caller handle timeouts
        raise
    
