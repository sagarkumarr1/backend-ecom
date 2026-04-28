from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count

from .models import Review, ReviewVote
from .serializers import ReviewSerializer, ReviewVoteSerializer
from products.models import Product
from orders.models import Order
from jwtapp.permissions import IsAdminUser


def _update_product_rating(product):
    result = Review.objects.filter(product=product, is_approved=True).aggregate(
        avg=Avg('rating'), count=Count('id')
    )
    product.avg_rating    = result['avg'] or 0.00
    product.total_reviews = result['count'] or 0
    product.save(update_fields=['avg_rating', 'total_reviews'])


class ProductReviewListView(APIView):
    """
    GET  /api/reviews/<product_slug>/       — product ke sabhi reviews
    POST /api/reviews/<product_slug>/       — review likhna (delivered customers only)
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        rating  = request.query_params.get('rating')
        qs      = Review.objects.filter(product=product, is_approved=True)
        if rating:
            qs = qs.filter(rating=rating)

        # Summary
        summary = qs.aggregate(avg=Avg('rating'), count=Count('id'))
        dist    = {}
        for i in range(1, 6):
            dist[str(i)] = qs.filter(rating=i).count()

        return Response({
            "summary": {
                "avg_rating":   round(summary['avg'] or 0, 2),
                "total":        summary['count'],
                "distribution": dist,
            },
            "reviews": ReviewSerializer(qs, many=True).data,
        })

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response({"error": "Login karo pehle."}, status=401)

        product = get_object_or_404(Product, slug=slug, status='active')

        # Already reviewed?
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response({"error": "Aapne pehle se review kiya hai."}, status=400)

        # Verified purchase check
        is_verified = Order.objects.filter(
            user=request.user,
            status='delivered',
            items__product=product
        ).exists()

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(
            product=product,
            user=request.user,
            is_verified_purchase=is_verified,
        )

        _update_product_rating(product)
        return Response(ReviewSerializer(review).data, status=201)


class MyReviewsView(APIView):
    """GET /api/reviews/my/ — apne saare reviews"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reviews = Review.objects.filter(user=request.user).select_related('product')
        return Response(ReviewSerializer(reviews, many=True).data)


class ReviewDetailView(APIView):
    """
    PATCH  /api/reviews/<id>/update/  — apna review edit karo
    DELETE /api/reviews/<id>/update/  — apna review delete karo
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        review = get_object_or_404(Review, pk=pk, user=request.user)
        serializer = ReviewSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _update_product_rating(review.product)
        return Response(ReviewSerializer(review).data)

    def delete(self, request, pk):
        review = get_object_or_404(Review, pk=pk, user=request.user)
        product = review.product
        review.delete()
        _update_product_rating(product)
        return Response({"message": "Review delete ho gaya."}, status=204)


class ReviewVoteView(APIView):
    """
    POST /api/reviews/<id>/vote/
    Body: {"vote": "helpful"} ya {"vote": "not_helpful"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        review     = get_object_or_404(Review, pk=pk)
        serializer = ReviewVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vote_type = serializer.validated_data['vote']

        existing = ReviewVote.objects.filter(review=review, user=request.user).first()
        if existing:
            if existing.vote == vote_type:
                existing.delete()
                msg = "Vote remove ho gaya."
            else:
                existing.vote = vote_type
                existing.save()
                msg = "Vote update ho gaya."
        else:
            ReviewVote.objects.create(review=review, user=request.user, vote=vote_type)
            msg = "Vote diya gaya!"

        # Update counts
        review.helpful_count     = review.votes.filter(vote='helpful').count()
        review.not_helpful_count = review.votes.filter(vote='not_helpful').count()
        review.save(update_fields=['helpful_count', 'not_helpful_count'])

        return Response({"message": msg})


# ── Admin ──────────────────────────────────────────────────────────────────
class AdminReviewListView(APIView):
    """GET /api/reviews/admin/ — sabhi reviews, approve/reject kar sakta hai"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = Review.objects.select_related('product', 'user')
        approved = request.query_params.get('is_approved')
        if approved is not None:
            qs = qs.filter(is_approved=(approved.lower() == 'true'))
        return Response(ReviewSerializer(qs, many=True).data)


class AdminReviewActionView(APIView):
    """PATCH /api/reviews/admin/<id>/ — approve/unapprove"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        review      = get_object_or_404(Review, pk=pk)
        is_approved = request.data.get('is_approved')
        if is_approved is not None:
            review.is_approved = bool(is_approved)
            review.save(update_fields=['is_approved'])
            _update_product_rating(review.product)
        return Response(ReviewSerializer(review).data)

    def delete(self, request, pk):
        review  = get_object_or_404(Review, pk=pk)
        product = review.product
        review.delete()
        _update_product_rating(product)
        return Response({"message": "Review delete ho gaya."}, status=204)
