{{ "#" * fullname | escape | length }}
{{ fullname | escape }}
{{ "#" * fullname | escape | length }}

.. contents::
   :local:

.. automodule:: {{ fullname }}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Module Attributes') }}

   .. autosummary::
      :nosignatures:
   {% for item in attributes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
      :nosignatures:
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
      :nosignatures:
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
      :nosignatures:
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% if attributes or classes or functions or exceptions %}
   {{ "#" * ["Detailed docs for", name, "module"] | join(" ") | length }}
   {{ ["Detailed docs for", name, "module"] | join(" ") }}
   {{ "#" * ["Detailed docs for", name, "module"] | join(" ") | length }}
   {% endif %}

   {% block detail_attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Attributes') }}
   {% for item in attributes %}
   .. autoattribute:: {{item}}
   {% endfor %}
   {% endif %}
   {% endblock %}

   {% block detail_classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}
   {% for item in classes %}
   .. autoclass:: {{item}}
      :members:
      :undoc-members:
      :show-inheritance:
   {% endfor %}
   {% endif %}
   {% endblock %}

   {% block detail_functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}
   {% for item in functions %}
   .. autofunction:: {{item}}
   {% endfor %}
   {% endif %}
   {% endblock %}

{% block modules %}
{% if modules %}
.. rubric:: Modules

.. autosummary::
   :toctree:
   :recursive:
{% for item in modules %}
   {% if ".test" not in item %}
   {{ item }}
   {% endif %}
{%- endfor %}
{% endif %}
{% endblock %}
