import logging

from redash import models, mail
from redash.destinations import *


class Email(BaseDestination):

    @classmethod
    def configuration_schema(cls):
        return {}

    def notify(self, alert_id, query_id, user_id, new_state, app, host, options):
        user = models.User.get_by_id(user_id)
        recipients = [user.email]
        alert = models.Alert.get_by_id(alert_id)
        html = """
        Check <a href="{host}/alerts/{alert_id}">alert</a> / check <a href="{host}/queries/{query_id}">query</a>.
        """.format(host=host, alert_id=alert.id, query_id=query.id)
        logging.debug("Notifying: %s", recipients)

        try:
            with app.app_context():
                message = Message(recipients=recipients,
                subject="[{1}] {0}".format(alert.name.encode('utf-8', 'ignore'), new_state.upper()),
                html=html)
            mail.send(message)
        except Exception:
            logging.exception("mail send ERROR.")

register(Email)