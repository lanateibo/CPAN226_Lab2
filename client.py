# This program was modified by Lana Teibo / N01739606

import socket
import argparse
import time
import os
import struct  # added sequence numbers to support reliability over UDP


def run_client(target_ip, target_port, input_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.25)  #timeout so we can resend if ACK is lost
    server_address = (target_ip, target_port)

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    try:
        seq = 0  #packet sequence number for stop-and-wait reliability

        with open(input_file, 'rb') as f:
            while True:
                chunk = f.read(4092)  # 4KB chunks

                if not chunk:
                    break

                header = struct.pack("!I", seq)  #4-byte big-endian sequence header
                packet = header + chunk          #attach header to payload

                # Stop-and-wait: send until correct ACK received
                while True:
                    sock.sendto(packet, server_address)  #resend same packet if needed

                    try:
                        ack, _ = sock.recvfrom(64)  #wait for ACK from server
                        if len(ack) >= 7 and ack[:3] == b"ACK":
                            ack_seq = struct.unpack("!I", ack[3:7])[0]
                            if ack_seq == seq:
                                break  # correct ACK
                    except socket.timeout:
                        continue  #on timeout, resend packet

                seq += 1  #only advance after receiving correct ACK

        # Send END marker (instead of empty packet) so EOF survives packet loss
        end_packet = b"END!" + struct.pack("!I", seq)  #explicit EOF marker with seq
        while True:
            sock.sendto(end_packet, server_address)  #resend END until ACK
            try:
                ack, _ = sock.recvfrom(64)
                if len(ack) >= 7 and ack[:3] == b"ACK":
                    ack_seq = struct.unpack("!I", ack[3:7])[0]
                    if ack_seq == seq:
                        break
            except socket.timeout:
                continue

        print("[*] File transmission complete.")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Sender (Stop-and-Wait)")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.target_port and args.file)
