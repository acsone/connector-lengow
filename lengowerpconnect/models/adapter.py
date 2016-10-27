# -*- coding: utf-8 -*-
# Copyright 2016 Cédric Pigeon
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import requests

from openerp.addons.connector.unit.backend_adapter import CRUDAdapter


class LengowCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for Lengow """

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(LengowCRUDAdapter, self).__init__(connector_env)

    def process_request(self, http_request, url, headers={}, params={},
                        data={}):
        response = http_request(url, headers=headers, params=params, data=data)
        if response.status_code != 200:
            error = response.json()
            message = '%s - %s' % (error['error']['code'],
                                   error['error']['message'])
            raise Exception(message)
        return response.json()

    def _get_token(self):
        url = '%s/access/get_token' % self.backend_record.location
        data = {'access_token': str(self.backend_record.access_token),
                'secret': str(self.backend_record.secret)}
        response = self.process_request(requests.post, url, data=data)
        return response['token'], response['user_id'], response['account_id']

    def _call(self, url, params, with_account=False):
        token, _, account_id = self._get_token()
        url = '%s/%s' % (self.backend_record.location, url)
        if with_account:
            params.update({'account_id': account_id})
        return self.process_request(requests.get,
                                    url,
                                    headers={'Authorization': token},
                                    params=params)


class LengowCRUDAdapter20(CRUDAdapter):
    """ External Records Adapter for Lengow """

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(LengowCRUDAdapter20, self).__init__(connector_env)

    def process_request(self, http_request, url, headers={}, params={},
                        data={}, ignore_result=False):
        response = http_request(url, headers=headers, params=params, data=data)
        if response.status_code != 200:
            error = response.json()
            message = '%s - %s' % (error['error']['code'],
                                   error['error']['message'])
            raise Exception(message)
        if not ignore_result:
            return response.json()
        return True

    def _call(self, url):
        url = '%s/%s' % (self.backend_record.location, url)
        return self.process_request(requests.get,
                                    url)


class GenericAdapter(LengowCRUDAdapter):

    _model_name = None
    _api = None

    def search(self, params, with_account=False):
        return self._call(self._api, params if params else {},
                          with_account=with_account)


class GenericAdapter20(LengowCRUDAdapter20):

    _model_name = None
    _api = None

    def search(self):
        return self._call(self._api)
