import re
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from .models import Customer, Product, Order


# --------------------------
# GraphQL Object Types
# --------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# --------------------------
# Input Types
# --------------------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime(required=False)


# --------------------------
# Mutation: Create Customer
# --------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, input):
        email = input.email.lower()

        # Email uniqueness validation
        if Customer.objects.filter(email=email).exists():
            raise GraphQLError("Email already exists.")

        # Optional phone format validation
        if input.phone:
            if not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', input.phone):
                raise GraphQLError("Invalid phone format. Use +1234567890 or 123-456-7890.")

        customer = Customer.objects.create(
            name=input.name,
            email=email,
            phone=input.phone
        )
        return CreateCustomer(customer=customer, message="Customer created successfully.")


# --------------------------
# Mutation: Bulk Create Customers
# --------------------------
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, input):
        created_customers = []
        errors = []

        for data in input:
            try:
                email = data.email.lower()

                if Customer.objects.filter(email=email).exists():
                    errors.append(f"Email '{email}' already exists.")
                    continue

                if data.phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', data.phone):
                    errors.append(f"Invalid phone format for '{data.name}'.")
                    continue

                customer = Customer(name=data.name, email=email, phone=data.phone)
                customer.save()
                created_customers.append(customer)

            except Exception as e:
                errors.append(f"Error creating {data.name}: {str(e)}")

        return BulkCreateCustomers(customers=created_customers, errors=errors)


# --------------------------
# Mutation: Create Product
# --------------------------
class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    def mutate(self, info, input):
        if Decimal(input.price) <= 0:
            raise GraphQLError("Price must be a positive number.")
        if input.stock is not None and input.stock < 0:
            raise GraphQLError("Stock cannot be negative.")

        product = Product.objects.create(
            name=input.name,
            price=input.price,
            stock=input.stock if input.stock is not None else 0
        )
        return CreateProduct(product=product)


# --------------------------
# Mutation: Create Order
# --------------------------
class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, input):
        # Validate customer existence
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            raise GraphQLError("Invalid customer ID.")

        # Validate products existence
        products = Product.objects.filter(pk__in=input.product_ids)
        if not products.exists():
            raise GraphQLError("No valid products found.")
        if len(products) != len(input.product_ids):
            raise GraphQLError("One or more product IDs are invalid.")

        # Calculate total amount
        total_amount = sum([p.price for p in products])

        # Create order
        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=input.order_date or timezone.now()
        )
        order.products.set(products)
        order.save()

        return CreateOrder(order=order)


# --------------------------
# Root Mutation Class
# --------------------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
