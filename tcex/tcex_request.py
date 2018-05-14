# -*- coding: utf-8 -*-
""" TcEx Framework Request Module """
from builtins import str
import json
from base64 import b64encode

from requests import (adapters, packages, Request, Session)
from requests.packages.urllib3.util.retry import Retry

packages.urllib3.disable_warnings()  # disable ssl warning message


def session_retry(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None):
    """Add retry to Requests Session

    https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.retry.Retry
    """
    session = session or Session()
    retries = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    # mount all https requests
    session.mount('https://', adapters.HTTPAdapter(max_retries=retries))
    return session


class TcExRequest(object):
    """Wrapper on Python Requests Module with API logging."""

    def __init__(self, tcex, session=None):
        """Initialize the Class properties."""
        self.tcex = tcex

        self._authorization_method = None
        self._basic_auth = None
        self._body = None
        self._content_type = None
        self._headers = {}
        self._http_method = 'GET'
        self._json = None
        self._payload = {}
        self._proxies = {}
        self._url = None
        self._files = None
        self._timeout = 300
        self._verify_ssl = False

        # session
        self.session = session_retry()
        if session is not None:
            self.session = session
        self.session.headers.update({'User-Agent': 'TcEx'})

    #
    # Body
    #

    @property
    def body(self):
        """The POST/PUT body content for this request."""
        return self._body

    @body.setter
    def body(self, data):
        """The POST/PUT body content for this request."""
        if data is not None:
            self._body = data
            self.add_header('Content-Length', str(len(self._body)))

    @property
    def json(self):
        """The POST/PUT body content in JSON format for this request."""
        return self._body

    @json.setter
    def json(self, data):
        """The POST/PUT body content in JSON format for this request."""
        if data is not None:
            self._body = json.dumps(data)
            self.add_header('Content-Type', 'application/json')

    #
    # HTTP Headers
    #

    @property
    def headers(self):
        """The header values for this request."""
        return self._headers

    def reset_headers(self):
        """Reset header dictionary for this request."""
        self._headers = {}

    def add_header(self, key, val):
        """Add a key value pair to header.

        Args:
            key (string): The header key
            val (string): The header value
        """
        self._headers[key] = str(val)

    @property
    def authorization(self):
        """The "Authorization" header value for this request."""
        return self._headers.get('Authorization')

    @authorization.setter
    def authorization(self, data):
        """The "Authorization" header value for this request."""
        self.add_header('Authorization', data)

    def authorization_method(self, method):
        """Method to create Authorization header for this request.

        Args:
            method (method): The method to use to generate the authorization header(s).
        """
        self._authorization_method = method

    @property
    def basic_auth(self):
        """The basic auth settings for this request."""
        return self._basic_auth

    @basic_auth.setter
    def basic_auth(self, data):
        """The basic auth settings for this request."""
        self._basic_auth = data

    @property
    def content_type(self):
        """The Content-Type header value for this request."""
        return self._content_type

    @content_type.setter
    def content_type(self, data):
        """The Content-Type header value for this request."""
        self._content_type = str(data)
        self.add_header('Content-Type', str(data))

    def set_basic_auth(self, username, password):
        """Manually set basic auth in the header when normal method does not work."""
        credentials = str(
            b64encode('{}:{}'.format(username, password).encode('utf-8')), 'utf-8')
        self.authorization = 'Basic {}'.format(credentials)

    @property
    def user_agent(self):
        """The the User-Agent header value for this request."""
        return self._headers.get('User-agent')

    @user_agent.setter
    def user_agent(self, data):
        """The the User-Agent header value for this request."""
        self.add_header('User-agent', data)

    #
    # HTTP Payload
    #

    @property
    def payload(self):
        """The payload values for this request."""
        return self._payload

    def reset_payload(self):
        """Reset payload dictionary"""
        self._payload = {}

    def add_payload(self, key, val, append=False):
        """Add a key value pair to payload for this request.

        Args:
            key (string): The payload key.
            val (string): The payload value.
            append (bool): Indicate whether the value should be appended or overwritten.
        """
        if append:
            self._payload.setdefault(key, []).append(val)
        else:
            self._payload[key] = val

    #
    # HTTP Method
    #

    @property
    def http_method(self):
        """The HTTP method for this request."""
        return self._http_method

    @http_method.setter
    def http_method(self, data):
        """The HTTP method for this request."""
        data = data.upper()
        if data in ['DELETE', 'GET', 'POST', 'PUT']:
            self._http_method = data

            # set content type for commit methods (best guess)
            if self._content_type is None and data in ['POST', 'PUT']:
                self.add_header('Content-Type', 'application/json')
        else:
            raise AttributeError(
                'Request Object Error: {} is not a valid HTTP method.'.format(data))

    #
    # Send Properties
    #

    @property
    def proxies(self):
        """The proxy settings for this request."""
        return self._proxies

    @proxies.setter
    def proxies(self, data):
        """The proxy settings for this request."""
        self._proxies = data

    @property
    def timeout(self):
        """The HTTP timeout value for this request."""
        return self._timeout

    @timeout.setter
    def timeout(self, data):
        """The HTTP timeout value for this request."""
        if isinstance(data, int):
            self._timeout = data

    @property
    def verify_ssl(self):
        """The SSL validation setting for this request."""
        return self._verify

    @verify_ssl.setter
    def verify_ssl(self, verify):
        """The SSL validation setting for this request.

        Args:
            data (string|boolean): A boolean for enable/disable or the server PEM file.
        """
        self._verify = verify

    @property
    def files(self):
        """Files setting for this request"""
        return self._files

    @files.setter
    def files(self, data):
        """Files setting for this request"""
        if isinstance(data, dict):
            self._files = data
    #
    # Send
    #

    def send(self, stream=False):
        """Send the HTTP request via Python Requests modules.

        This method will send the request to the remote endpoint.  It will try to handle
        temporary communications issues by retrying the request automatically.

        Args:
            stream (boolean): Boolean to enable stream download.

        Returns:
            (Requests.Response) The Request response
        """
        #
        # prepare request
        #

        api_request = Request(
            method=self._http_method, url=self._url, data=self._body, files=self._files,
            params=self._payload)

        request_prepped = api_request.prepare()

        # add authorization header returned by authorization method
        if self._authorization_method is not None:
            self._headers.update(self._authorization_method(request_prepped))
        request_prepped.prepare_headers(self._headers)
        # self.tcex.log.debug(u'Request URL: {}'.format(self._url))

        if self._basic_auth is not None:
            request_prepped.prepare_auth(self._basic_auth)

        #
        # api request (gracefully handle temporary communications issues with the API)
        #
        try:
            response = self.session.send(
                request_prepped, proxies=self._proxies, timeout=self._timeout,
                verify=self._verify_ssl, stream=stream)
        except Exception as e:
            err = 'Failed making HTTP request ({}).'.format(e)
            raise RuntimeError(err)

        # self.tcex.log.info(u'URL ({}): {}'.format(self._http_method, response.url))
        self.tcex.log.info(u'Status Code: {}'.format(response.status_code))
        return response

    #
    # URL
    #

    @property
    def url(self):
        """The URL for this request."""
        return self._url

    @url.setter
    def url(self, data):
        """The URL for this request."""
        self._url = data

    def __str__(self):
        """Print this request instance configuration."""
        printable_string = '\n{0!s:_^80}\n'.format('Request')

        #
        # http settings
        #
        printable_string += '\n{0!s:40}\n'.format('HTTP Settings')
        printable_string += '  {0!s:<29}{1!s:<50}\n'.format('HTTP Method', self.http_method)
        printable_string += '  {0!s:<29}{1!s:<50}\n'.format('Request URL', self.url)
        printable_string += '  {0!s:<29}{1!s:<50}\n'.format('Content Type', self.content_type)
        printable_string += '  {0!s:<29}{1!s:<50}\n'.format('Body', self.body)

        #
        # headers
        #
        if self.headers:
            printable_string += '\n{0!s:40}\n'.format('Headers')
            for k, v in self.headers.items():
                printable_string += '  {0!s:<29}{1!s:<50}\n'.format(k, v)

        #
        # payload
        #
        if self.payload:
            printable_string += '\n{0!s:40}\n'.format('Payload')
            for k, v in self.payload.items():
                printable_string += '  {0!s:<29}{1!s:<50}\n'.format(k, v)

        return printable_string
