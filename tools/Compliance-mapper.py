governance-standards/tools/compliance-mapper.py

```python
#!/usr/bin/env python3
"""
Compliance Framework Mapper
Maps governance policies to compliance standards.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass


@dataclass
class ComplianceControl:
    id: str
    title: str
    description: str
    severity: str
    checks: List[Dict]


@dataclass
class ComplianceStandard:
    id: str
    name: str
    version: str
    controls: List[ComplianceControl]


class ComplianceMapper:
    def __init__(self, standards_dir: str):
        self.standards_dir = Path(standards_dir)
        self.standards = self._load_standards()
    
    def _load_standards(self) -> Dict[str, ComplianceStandard]:
        """Load all compliance standards."""
        standards = {}
        
        for file_path in self.standards_dir.glob("*.yaml"):
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                
                standard_info = data['standard']
                controls = []
                
                for control_data in data.get('controls', []):
                    control = ComplianceControl(
                        id=control_data['id'],
                        title=control_data['title'],
                        description=control_data['description'],
                        severity=control_data.get('severity', 'medium'),
                        checks=control_data.get('checks', [])
                    )
                    controls.append(control)
                
                standard = ComplianceStandard(
                    id=standard_info['id'],
                    name=standard_info['name'],
                    version=standard_info['version'],
                    controls=controls
                )
                
                standards[standard.id] = standard
        
        return standards
    
    def map_policy_to_standards(self, policy: Dict) -> Dict[str, List[str]]:
        """Map a policy to compliance standards."""
        mapping = {}
        
        # Check policy metadata for compliance references
        metadata = policy.get('metadata', {})
        compliance_refs = metadata.get('compliance', [])
        
        for ref in compliance_refs:
            # Parse reference format: STANDARD-ID[-CONTROL-ID]
            parts = ref.split('-')
            standard_id = '-'.join(parts[:2]) if len(parts) >= 2 else ref
            
            if standard_id in self.standards:
                if standard_id not in mapping:
                    mapping[standard_id] = []
                
                # If specific control is referenced
                if len(parts) > 2:
                    control_id = '-'.join(parts[2:])
                    mapping[standard_id].append(control_id)
        
        return mapping
    
    def generate_compliance_report(self, policies: List[Dict]) -> Dict:
        """Generate compliance report for multiple policies."""
        report = {
            "summary": {
                "total_policies": len(policies),
                "standards_covered": set(),
                "controls_covered": {}
            },
            "details": {}
        }
        
        for policy in policies:
            policy_name = policy.get('metadata', {}).get('name', 'unknown')
            mapping = self.map_policy_to_standards(policy)
            
            report["details"][policy_name] = {
                "policy_name": policy_name,
                "standards": mapping
            }
            
            # Update summary
            for standard_id, controls in mapping.items():
                report["summary"]["standards_covered"].add(standard_id)
                
                if standard_id not in report["summary"]["controls_covered"]:
                    report["summary"]["controls_covered"][standard_id] = set()
                
                report["summary"]["controls_covered"][standard_id].update(controls)
        
        # Convert sets to lists for JSON serialization
        report["summary"]["standards_covered"] = list(report["summary"]["standards_covered"])
        for standard_id in report["summary"]["controls_covered"]:
            report["summary"]["controls_covered"][standard_id] = list(
                report["summary"]["controls_covered"][standard_id]
            )
        
        return report
    
    def check_compliance_gap(self, 
                            required_standard: str, 
                            required_controls: List[str],
                            policies: List[Dict]) -> Dict:
        """Check gap between required controls and implemented policies."""
        if required_standard not in self.standards:
            raise ValueError(f"Standard {required_standard} not found")
        
        standard = self.standards[required_standard]
        implemented_controls = set()
        
        # Find implemented controls
        for policy in policies:
            mapping = self.map_policy_to_standards(policy)
            if required_standard in mapping:
                implemented_controls.update(mapping[required_standard])
        
        # Calculate gaps
        required_set = set(required_controls)
        missing_controls = required_set - implemented_controls
        implemented_controls = implemented_controls & required_set
        
        return {
            "standard": required_standard,
            "required_controls": required_controls,
            "implemented_controls": list(implemented_controls),
            "missing_controls": list(missing_controls),
            "coverage_percentage": len(implemented_controls) / len(required_controls) * 100
        }


def main():
    """CLI interface for compliance mapping."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Map policies to compliance standards')
    parser.add_argument('--policies', '-p', required=True, help='Directory containing policies')
    parser.add_argument('--standards', '-s', default='standards/', help='Standards directory')
    parser.add_argument('--output', '-o', help='Output file (JSON)')
    parser.add_argument('--format', choices=['json', 'html', 'csv'], default='json')
    
    args = parser.parse_args()
    
    # Load policies
    policies = []
    policies_dir = Path(args.policies)
    
    for file_path in policies_dir.glob("*.yaml"):
        with open(file_path, 'r') as f:
            policies.append(yaml.safe_load(f))
    
    for file_path in policies_dir.glob("*.yml"):
        with open(file_path, 'r') as f:
            policies.append(yaml.safe_load(f))
    
    # Generate compliance report
    mapper = ComplianceMapper(args.standards)
    report = mapper.generate_compliance_report(policies)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            if args.format == 'json':
                json.dump(report, f, indent=2)
            elif args.format == 'csv':
                # Convert to CSV
                import csv
                writer = csv.writer(f)
                writer.writerow(['Policy', 'Standard', 'Controls'])
                for policy_name, details in report['details'].items():
                    for standard_id, controls in details['standards'].items():
                        writer.writerow([policy_name, standard_id, ';'.join(controls)])
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
