#!/usr/bin/env python
"""
Test script for metrics_snap functionality.
Tests with a small subset of subnets to verify the system works.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.bittensor.metrics import calculate_subnet_metrics
from models import MetricsSnap, SubnetMeta, ScreenerRaw
from services.db import get_db

def test_metrics_snap():
    """Test metrics_snap with a few subnets."""
    print("🧪 Testing metrics_snap functionality...")
    
    # Test with just a few subnets
    test_subnets = [1, 2, 3, 64]  # Small test set
    
    snapshot_time = datetime.utcnow()
    
    with get_db() as session:
        successful_snapshots = 0
        
        for netuid in test_subnets:
            try:
                print(f"Processing subnet {netuid}...")
                
                # Get SDK metrics for this subnet
                metrics = calculate_subnet_metrics(netuid)
                
                if "error" in metrics:
                    print(f"❌ Error getting metrics for subnet {netuid}: {metrics['error']}")
                    continue
                
                # Get subnet metadata for reference
                subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
                
                # Create metrics snapshot record
                snapshot = MetricsSnap(
                    timestamp=snapshot_time,
                    netuid=netuid,
                    
                    # Market metrics (will be filled from screener data later)
                    market_cap_tao=None,  # TODO: Join with screener data
                    flow_24h=None,        # TODO: Join with screener data
                    price_tao=None,       # TODO: Join with screener data
                    
                    # SDK metrics
                    total_stake_tao=metrics.get('total_stake_tao'),
                    stake_hhi=metrics.get('stake_hhi'),
                    uid_count=metrics.get('uid_count'),
                    mean_incentive=metrics.get('mean_incentive'),
                    p95_incentive=metrics.get('p95_incentive'),
                    consensus_alignment=metrics.get('consensus_alignment'),
                    trust_score=metrics.get('trust_score'),
                    mean_consensus=metrics.get('mean_consensus'),
                    pct_aligned=metrics.get('pct_aligned'),
                    
                    # Emission metrics
                    emission_owner=metrics.get('emission_split', {}).get('owner'),
                    emission_miners=metrics.get('emission_split', {}).get('miners'),
                    emission_validators=metrics.get('emission_split', {}).get('validators'),
                    total_emission_tao=metrics.get('total_emission_tao'),
                    tao_in_emission=metrics.get('tao_in_emission'),
                    alpha_out_emission=metrics.get('alpha_out_emission'),
                    
                    # Network activity metrics
                    active_validators=metrics.get('active_validators'),
                    
                    # Metadata
                    subnet_name=subnet_meta.subnet_name if subnet_meta else None,
                    category=subnet_meta.primary_category if subnet_meta else None,
                    confidence=subnet_meta.confidence if subnet_meta else None
                )
                
                session.add(snapshot)
                successful_snapshots += 1
                
                print(f"✅ Subnet {netuid}: {metrics.get('uid_count', 0)} UIDs, {metrics.get('total_stake_tao', 0):.2f} TAO staked")
                
            except Exception as e:
                print(f"❌ Error processing subnet {netuid}: {e}")
                continue
        
        # Commit all snapshots
        session.commit()
        
        print(f"\n📊 Test complete: {successful_snapshots}/{len(test_subnets)} subnets processed successfully")
        
        # Show some sample data
        if successful_snapshots > 0:
            print("\n📋 Sample metrics_snap data:")
            recent_snapshots = session.query(MetricsSnap).order_by(MetricsSnap.timestamp.desc()).limit(3).all()
            
            for snapshot in recent_snapshots:
                print(f"  Subnet {snapshot.netuid} ({snapshot.subnet_name}):")
                print(f"    Stake: {snapshot.total_stake_tao:.2f} TAO, UIDs: {snapshot.uid_count}")
                print(f"    HHI: {snapshot.stake_hhi:.2f}, Incentive: {snapshot.mean_incentive:.6f}")
                print(f"    Emissions: O:{snapshot.emission_owner:.3f} M:{snapshot.emission_miners:.3f} V:{snapshot.emission_validators:.3f}")
                print()

if __name__ == "__main__":
    test_metrics_snap() 