import paramiko


class SFTPClient(paramiko.SFTPClient):
    """
    overriding the paramiko SFTPClient to provide alteration of buffer read length
    """
    def __init__(self, sock, buffer_read_length=32768):
        super(SFTPClient, self).__init__(sock)
        self.buffer_read_length = buffer_read_length

    @classmethod
    def from_transport(cls, t, window_size=None, max_packet_size=None, buffer_read_length=32768):
        """
        Create an SFTP client channel from an open `.Transport`.
        Setting the window and packet sizes might affect the transfer speed.
        The default settings in the `.Transport` class are the same as in
        OpenSSH and should work adequately for both files transfers and
        interactive sessions.
        :param .Transport t: an open `.Transport` which is already
            authenticated
        :param int window_size:
            optional window size for the `.SFTPClient` session.
        :param int max_packet_size:
            optional max packet size for the `.SFTPClient` session..
        :return:
            a new `.SFTPClient` object, referring to an sftp session (channel)
            across the transport
        .. versionchanged:: 1.15
            Added the ``window_size`` and ``max_packet_size`` arguments.
        """
        chan = t.open_session(window_size=window_size,
                              max_packet_size=max_packet_size)
        if chan is None:
            return None
        chan.invoke_subsystem('sftp')
        return cls(chan, buffer_read_length)

    def _transfer_with_callback(self, reader, writer, file_size, callback):
        size = 0
        while True:
            data = reader.read(self.buffer_read_length)
            writer.write(data)
            size += len(data)
            if len(data) == 0:
                break
            if callback is not None:
                callback(size, file_size)
        return size
