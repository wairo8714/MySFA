from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class HealthCheckMiddleware(MiddlewareMixin):
    """
    ヘルスチェックエンドポイントでSSLリダイレクトを無効化するミドルウェア
    ALBのヘルスチェックはHTTPで行われるため、301リダイレクトを防ぐ
    """

    def process_request(self, request):
        # ヘルスチェックエンドポイントの場合は、SSLリダイレクトを無効化
        if request.path == "/health/":
            # SECURE_SSL_REDIRECTを一時的に無効化
            # これはprocess_responseで処理する
            return None
        return None

    def process_response(self, request, response):
        # ヘルスチェックエンドポイントで301リダイレクトが発生した場合、200を返す
        if request.path == "/health/" and response.status_code == 301:
            return JsonResponse({"status": "healthy"}, status=200)
        return response
