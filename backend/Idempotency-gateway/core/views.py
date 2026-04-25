import hashlib
import json
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import IdempotencyRecord
from .utils import get_lock_for_key


class ProcessPaymentView(APIView):

    def post(self, request):
        # Step 1: Get the Idempotency-Key from headers
        idempotency_key = request.headers.get('Idempotency-Key')

        # Step 2: Check if key exists in headers
        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 3: Hash the request body
        request_data = request.data
        body_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()

        # Step 4: Get lock for this specific key
        lock = get_lock_for_key(idempotency_key)

        with lock:
            # Step 5: Check if key already exists in DB
            try:
                record = IdempotencyRecord.objects.get(key=idempotency_key)

                # Step 6: Same key, different body → 422 error
                if record.request_body_hash != body_hash:
                    return Response(
                        {"error": "Idempotency key already used for a different request body."},
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )

                # Step 7: Same key, same body → return cached response
                cached_response = Response(
                    record.response_body,
                    status=record.status_code
                )
                cached_response['X-Cache-Hit'] = 'true'
                return cached_response

            except IdempotencyRecord.DoesNotExist:
                pass

            # Step 8: New key → mark as processing
            record = IdempotencyRecord.objects.create(
                key=idempotency_key,
                request_body_hash=body_hash,
                response_body={},
                status_code=0,
                is_processing=True
            )

            # Step 9: Simulate payment processing (2 second delay)
            time.sleep(2)

            # Step 10: Build the response
            amount = request_data.get('amount')
            currency = request_data.get('currency')
            response_body = {"message": f"Charged {amount} {currency}"}

            # Step 11: Save the response to DB
            record.response_body = response_body
            record.status_code = 201
            record.is_processing = False
            record.save()

            return Response(response_body, status=status.HTTP_201_CREATED)