"""Serializers for the eBay connection and setup forms."""

from rest_framework import serializers

HANDLING_DAYS = [1, 2, 3, 4, 5, 10]
RETURN_DAYS = [14, 30, 60]
COST_PAYERS = ["BUYER", "SELLER"]


class ConnectFinishSerializer(serializers.Serializer):
    """Validate the redirect URL pasted after the eBay login."""

    redirect_url = serializers.CharField(max_length=4000)


class PolicyFormSerializer(serializers.Serializer):
    """Validate the shipping, return and payment settings of the setup form."""

    shipping_service = serializers.CharField(max_length=100)
    shipping_cost = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0)
    handling_days = serializers.ChoiceField(choices=HANDLING_DAYS)
    return_days = serializers.ChoiceField(choices=RETURN_DAYS)
    return_cost_payer = serializers.ChoiceField(choices=COST_PAYERS)
