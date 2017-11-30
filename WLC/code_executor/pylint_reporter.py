import sys
from pylint.interfaces import IReporter
from pylint.reporters import BaseReporter


class CustomJSONReporter(BaseReporter):
    """Report messages and layouts in JSON."""

    __implements__ = IReporter
    name = 'json_custom'
    extension = 'json_custom'

    def __init__(self, output=sys.stdout):
        BaseReporter.__init__(self, output)
        self.messages = []

    def handle_message(self, msg):
        """Manage message of different type and in the context of path."""
        self.messages.append({
            'type': msg.category,
            'module': msg.module,
            'obj': msg.obj,
            'line': msg.line,
            'column': msg.column,
            'path': msg.path,
            'symbol': msg.symbol,
            'message': msg.msg,
            'message-id': msg.msg_id,
        })

    def get_errors_json(self):
        return self.messages

    def display_messages(self, layout):
        """Don't do nothing in this reporter."""

    def display_reports(self, layout): # pylint: disable=arguments-differ
        """Don't do nothing in this reporter."""

    def _display(self, layout):
        """Don't do nothing."""
