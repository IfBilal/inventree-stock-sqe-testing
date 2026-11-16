"""Verbatim extract of StockAdjustmentItemSerializer.validate_pk (upstream stock/serializers.py L1835-1850) as a module-level function, so SonarQube reports its complexity per file."""
def validate_pk(self, stock_item: StockItem) -> StockItem:
    """Ensure the stock item is valid."""
    if self.require_in_stock == True:
        allow_out_of_stock_transfer = get_global_setting(
            'STOCK_ALLOW_OUT_OF_STOCK_TRANSFER', backup_value=False, cache=False
        )

        if not allow_out_of_stock_transfer and not stock_item.is_in_stock(
            check_status=False, check_quantity=False, check_in_production=False
        ):
            raise ValidationError(_('Stock item is not in stock'))
    elif self.require_in_stock == False:
        if stock_item.is_in_stock():
            raise ValidationError(_('Stock item is already in stock'))

    return stock_item
