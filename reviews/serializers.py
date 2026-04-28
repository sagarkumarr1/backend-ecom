from rest_framework import serializers
from .models import Review, ReviewVote


class ReviewSerializer(serializers.ModelSerializer):
    user_name            = serializers.CharField(source='user.full_name', read_only=True)
    is_verified_purchase = serializers.ReadOnlyField()

    class Meta:
        model  = Review
        fields = (
            'id', 'product', 'user_name', 'rating', 'title', 'body',
            'images', 'is_verified_purchase', 'is_approved',
            'helpful_count', 'not_helpful_count', 'created_at',
        )
        read_only_fields = ('id', 'product', 'is_approved', 'helpful_count',
                            'not_helpful_count', 'created_at')

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating 1 se 5 ke beech honi chahiye.")
        return value


class ReviewVoteSerializer(serializers.Serializer):
    vote = serializers.ChoiceField(choices=['helpful', 'not_helpful'])
