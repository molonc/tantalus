from rest_framework import serializers
from rest_framework.renderers import BrowsableAPIRenderer, HTMLFormRenderer


class HTMLFormRendererImproved(HTMLFormRenderer):
    """Never renders select boxes for related fields."""

    def __init__(self):
        """Use text inputs for related fields."""
        self.default_style[serializers.RelatedField] = {
            "base_template": "input.html",
            "input_type": "text",
        }
        self.default_style[serializers.ManyRelatedField] = {
            "base_template": "input.html",
            "input_type": "text",
        }


class BrowsableAPIRendererImproved(BrowsableAPIRenderer):
    """Use an improved form renderer."""

    form_renderer_class = HTMLFormRendererImproved
