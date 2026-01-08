class TenantContext:
    current_tenant = "default"

    @classmethod
    def set(cls, tenant):
        cls.current_tenant = tenant

    @classmethod
    def get(cls):
        return cls.current_tenant
