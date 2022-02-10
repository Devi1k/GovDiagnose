from multiprocessing import Pipe, Process


def slotValueRecognition(end_flag, pipe):
    in_pipe, out_pipe = pipe

    while True:
        try:
            msg = in_pipe.recv()
            print("slotRec getting", msg)
            out_pipe.send(msg)
            if msg == end_flag:
                break
        except EOFError:
            break

    in_pipe.close()
    out_pipe.close()
