# This program was modified by Lana Teibo / N01739606

import socket
import argparse
import struct  # unpack sequence numbers + build ACKs for reliability


def run_server(port, output_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 2. Bind the socket to the port (0.0.0.0 means all interfaces)
    server_address = ("", port)
    sock.bind(server_address)

    print(f"[*] Server listening on port {port}")
    print("[*] Server will save each received file as 'received_<ip>_<port>.jpg' based on sender.")

    try:
        while True:
            f = None
            sender_filename = None

            expected_seq = 0  # track next expected sequence number
            buffer = {}       # store out-of-order packets until missing ones arrive

            print("==== Waiting for a new transfer ====")

            while True:
                packet, addr = sock.recvfrom(4096)  # relay buffer is 4096, keep receive size consistent

                # END marker: b"END!" + 4-byte seq  -> total 8 bytes
                if len(packet) == 8 and packet[:4] == b"END!":
                    end_seq = struct.unpack("!I", packet[4:8])[0]  # read END seq
                    ack = b"ACK" + struct.pack("!I", end_seq)       # ACK END so client can finish
                    sock.sendto(ack, addr)

                    # flush any remaining buffered packets that are now contiguous
                    while expected_seq in buffer:
                        if f is not None:
                            f.write(buffer.pop(expected_seq))
                        expected_seq += 1

                    print(f"[*] End-of-file marker received from {addr}. Closing file.")
                    break

                # Must have at least 4 bytes for seq header
                if len(packet) < 4:
                    continue

                seq = struct.unpack("!I", packet[:4])[0]  #extract sequence number
                data = packet[4:]                        

                # Open file on first valid data packet
                if f is None:
                    print("==== Start of reception ====")
                    ip, sender_port = addr
                    sender_filename = f"received_{ip.replace('.', '_')}_{sender_port}.jpg"
                    f = open(sender_filename, "wb")
                    print(f"[*] First packet received from {addr}. File opened for writing as '{sender_filename}'.")

                # Always ACK what we received (even duplicates/out-of-order)
                ack = b"ACK" + struct.pack("!I", seq) # ACK each packet so client can move on
                sock.sendto(ack, addr)

                # buffering logic to handle reordering
                if seq == expected_seq:
                    f.write(data)  # write expected packet
                    expected_seq += 1

                    # flush any buffered packets that now follow in order
                    while expected_seq in buffer:
                        f.write(buffer.pop(expected_seq))
                        expected_seq += 1

                elif seq > expected_seq:
                    #store out-of-order packet for later
                    if seq not in buffer:  # avoid overwriting if duplicate arrives
                        buffer[seq] = data
                # else: seq < expected_seq -> duplicate, ignore

            if f:
                f.close()
            print("==== End of reception ====")

    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()
        print("[*] Server socket closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Receiver (Stop-and-Wait + Buffering)")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    run_server(args.port, args.output)
