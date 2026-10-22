"""Keep local render checks off production services; local failures stay real."""
from urllib.parse import urlparse


TELEMETRY_HOSTS = {'mc.yandex.ru', 'mc.yandex.com', 'mc.webvisor.org'}


def handle_external(route, request, origin, observed):
    parsed, local = urlparse(request.url), urlparse(origin)
    if (parsed.scheme, parsed.netloc) == (local.scheme, local.netloc):
        return False
    telemetry = parsed.hostname in TELEMETRY_HOSTS
    observed.append({'url': request.url, 'method': request.method,
                     'disposition': 'inert_external_telemetry' if telemetry else 'rejected_external_resource'})
    if telemetry:
        route.fulfill(status=204, body='')
    else:
        route.abort('blockedbyclient')
    return True


def isolate_local_page(page, origin):
    observed = []
    def handler(route, request):
        if not handle_external(route, request, origin, observed):
            route.continue_()
    page.route('**/*', handler)
    return observed
