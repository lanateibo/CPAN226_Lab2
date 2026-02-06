# This program was modified by Lana Teibo / N01739606

import socket
import argparse
import struct  # unpack sequence numbers + build ACKs for reliability


def run_server(port, output_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 2. Bind the socket to the port (0.0.0.0 means all interfaces)
    server_address = ('', port)
    print(f"[*] Server listening on port {port}")
    print(f"[*] Server will save each received file as 'received_<ip>_<port>.jpg' based on sender.")
    sock.bind(server_address)


    try:
        while True:
            f = None
            sender_filename = None
            expected_seq = 0  # track next expected sequence (stop duplicates)

            print("==== Waiting for a new transfer ====")

            while True:
                packet, addr = sock.recvfrom(65535)

                # Handle END marker: b"END!" + 4-byte seq
                if len(packet) == 8 and packet[:4] == b"END!":
                    end_seq = struct.unpack("!I", packet[4:8])[0]  # read END seq
                    ack = b"ACK" + struct.pack("!I", end_seq)       # ACK END so client can finish
                    sock.sendto(ack, addr)

                    print(f"[*] End-of-file marker received from {addr}. Closing file.")
                    break

                # Must have at least 4 bytes for seq header
                if len(packet) < 4:
                    continue

                seq = struct.unpack("!I", packet[:4])[0]  # extract sequence number
                data = packet[4:]                          # payload bytes

                # Open file on first valid data packet
                if f is None:
                    print("==== Start of reception ====")
                    ip, sender_port = addr
                    sender_filename = f"received_{ip.replace('.', '_')}_{sender_port}.jpg"
                    f = open(sender_filename, 'wb')
                    print(f"[*] First packet received from {addr}. File opened for writing as '{sender_filename}'.")

                # Always ACK what we received 
                ack = b"ACK" + struct.pack("!I", seq)  # send ACK for reliability
                sock.sendto(ack, addr)

                # Only write expected packet 
                if seq == expected_seq:
                    f.write(data)  #write only in-order to prevent duplicates
                    expected_seq += 1
               

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
    parser = argparse.ArgumentParser(description="Reliable UDP File Receiver (Stop-and-Wait)")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    try:
        run_server(args.port, args.output)
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
