# This program was modified by Lana Teibo / N01739606

import socket
import argparse
import os
import struct  # IMPROVEMENT: add sequence numbers for reliability over UDP


def run_client(target_ip, target_port, input_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.25)  # IMPROVEMENT: timeout enables resend when ACK is lost
    server_address = (target_ip, target_port)

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    try:
        seq = 0  # IMPROVEMENT: stop-and-wait sequence number

        with open(input_file, "rb") as f:
            while True:
                chunk = f.read(4092)  # IMPROVEMENT: 4092 + 4 header = 4096 max for relay buffer
                if not chunk:
                    break

                packet = struct.pack("!I", seq) + chunk  # IMPROVEMENT: header + payload

                retries = 0  # IMPROVEMENT: track resend attempts
                while True:
                    sock.sendto(packet, server_address)  # IMPROVEMENT: resend until ACK received
                    try:
                        ack, _ = sock.recvfrom(64)
                        if len(ack) >= 7 and ack[:3] == b"ACK":
                            ack_seq = struct.unpack("!I", ack[3:7])[0]
                            if ack_seq == seq:
                                break
                    except socket.timeout:
                        retries += 1
                        if retries % 20 == 0:
                            print(f"[*] Waiting for ACK seq={seq} (retries={retries})")  # IMPROVEMENT: progress output
                    except ConnectionResetError:
                        # IMPROVEMENT: Windows can raise this when relay drops packets; keep retrying
                        continue

                seq += 1  # IMPROVEMENT: move to next chunk only after correct ACK

        # Send END marker reliably (do NOT use empty packet EOF)
        end_seq = seq
        end_packet = b"END!" + struct.pack("!I", end_seq)  # IMPROVEMENT: explicit EOF marker survives loss

        retries = 0  # IMPROVEMENT: resend END until ACK
        while True:
            sock.sendto(end_packet, server_address)
            try:
                ack, _ = sock.recvfrom(64)
                if len(ack) >= 7 and ack[:3] == b"ACK":
                    ack_seq = struct.unpack("!I", ack[3:7])[0]
                    if ack_seq == end_seq:
                        break
            except socket.timeout:
                retries += 1
                if retries % 20 == 0:
                    print(f"[*] Waiting for END ACK (retries={retries})")  # IMPROVEMENT: progress output
            except ConnectionResetError:
                continue

        print("[*] File transmission complete.")

    finally:
        sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Sender (Stop-and-Wait)")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)
