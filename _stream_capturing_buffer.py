from io import StringIO, TextIOBase
from threading import Thread
from typing import IO


class StreamCapturingBuffer(Thread):
    """Capture the lines written to a stream and write them to the target stream and a buffer."""

    def __init__(self, *, input_stream: IO[str], output_stream: TextIOBase):
        Thread.__init__(self, daemon=True)
        self._input_stream = input_stream
        self._output_stream = output_stream
        self._buffer = StringIO()
        self._write_to_buffer = True
        self._stopped = False

    def run(self):
        input_stream_lines_iterator = iter(self._input_stream.readline, b"")
        for line in input_stream_lines_iterator:
            self._write(line)
            if self._stopped:
                break

    def _write(self, line: str):
        if self._write_to_buffer:
            self._buffer.write(line)
        self._output_stream.write(line)

    def skip_writing_to_buffer(self):
        self._write_to_buffer = False

    def get_buffer_value(self) -> str:
        return self._buffer.getvalue()

    def stop(self):
        self._stopped = True
