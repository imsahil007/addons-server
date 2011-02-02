import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.cache import patch_vary_headers


# We do this in zeus for performance, so this exists as a POC and to work out
# the logic.
class DetectMobileMiddleware(object):
    # Mobile user agents.
    UA = re.compile('android|fennec|iemobile|iphone|opera (?:mini|mobi)')
    # We set a cookie if you explicitly select mobile/no mobile.
    MC = 'mamo'

    def process_request(self, request):
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        mc = request.COOKIES.get(self.MC)
        if (self.UA.search(ua) and mc != 'off') or mc == 'on':
            request.META['HTTP_X_MOBILE'] = '1'

    def process_response(self, request, response):
        patch_vary_headers(response, ['User-Agent'])
        return response


class XMobileMiddleware(object):

    def redirect(self, request, base):
        path = base.rstrip('/') + request.path
        if request.GET:
            path += '?' + request.GET.urlencode()
        response = HttpResponsePermanentRedirect(path)
        response['Vary'] = 'X-Mobile'
        return response

    def process_view(self, request, view_func, args, kwargs):
        try:
            want_mobile = int(request.META.get('HTTP_X_MOBILE', 0))
        except Exception:
            want_mobile = False
        # SERVER_NAME doesn't work on devserver, HOST cannot be trusted in
        # production.
        header = 'HTTP_HOST' if settings.DEBUG else 'SERVER_NAME'
        on_mobile = request.META[header] == settings.MOBILE_DOMAIN
        has_mobile = getattr(view_func, 'mobile', False)
        if want_mobile and has_mobile and not on_mobile:
            return self.redirect(request, settings.MOBILE_SITE_URL)
        if not (want_mobile and has_mobile) and on_mobile:
            return self.redirect(request, settings.SITE_URL)
        request.MOBILE = want_mobile

    def process_response(self, request, response):
        patch_vary_headers(response, ['X-Mobile'])
        return response
