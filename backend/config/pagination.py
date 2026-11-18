from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """সব list API-তে ব্যবহার হয়। ?page=2&page_size=50 দিয়ে নিয়ন্ত্রণ করা যায়।"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
