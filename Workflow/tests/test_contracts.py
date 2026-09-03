import unittest

from Workflow.core.contracts import ContractError, validate_design_shape


class ContractTests(unittest.TestCase):
    def test_complete_design_shape(self):
        value = {"format_version": 1, "design_version": 1}
        for name in (
            "project", "requirements", "architecture", "interfaces",
            "implementation", "budgets", "verification",
        ):
            value[name] = {"value": True}
        self.assertIs(value, validate_design_shape(value))

    def test_missing_section_is_rejected(self):
        with self.assertRaises(ContractError):
            validate_design_shape({"format_version": 1, "design_version": 1})


if __name__ == "__main__":
    unittest.main()

