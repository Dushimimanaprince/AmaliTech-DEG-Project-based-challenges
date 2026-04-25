import hashlib
import json
import time
from django.utils import timezone
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import IdempotencyRecord
from .utils import get_lock_for_key


class ProcessPaymentView(APIView):

    def post(self, request):

        idempotency_key = request.headers.get('Idempotency-Key')


        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header is required"},
                status=status.HTTP_400_BAD_REQUEST
            )


        request_data = request.data
        body_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()


        lock = get_lock_for_key(idempotency_key)

        with lock:

            try:
                record = IdempotencyRecord.objects.get(key=idempotency_key)

                if timezone.now() - record.created_at > timedelta(hours=24):
                    record.delete()
                    raise IdempotencyRecord.DoesNotExist

                if record.request_body_hash != body_hash:
                    return Response(
                        {"error": "Idempotency key already used for a different request body."},
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )


                cached_response = Response(
                    record.response_body,
                    status=record.status_code
                )
                cached_response['X-Cache-Hit'] = 'true'
                return cached_response

            except IdempotencyRecord.DoesNotExist:
                pass


            record = IdempotencyRecord.objects.create(
                key=idempotency_key,
                request_body_hash=body_hash,
                response_body={},
                status_code=0,
                is_processing=True
            )

            time.sleep(2)


            amount = request_data.get('amount')
            currency = request_data.get('currency')
            response_body = {"message": f"Charged {amount} {currency}"}


            record.response_body = response_body
            record.status_code = 201
            record.is_processing = False
            record.save()

            return Response(response_body, status=status.HTTP_201_CREATED)