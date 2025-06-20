import copy
from collections import defaultdict
from math import ceil, log2


class MemoryBlock:
    def __init__(self, start, size, status='free', job_id=None):
        self.start = start
        self.size = size
        self.status = status  # 'free' or 'used'
        self.job_id = job_id
    def __repr__(self):
        return f"<Block start={self.start} size={self.size} status={self.status}>"


class MemoryManager:
    def __init__(self, total_size=400, enable_merge=True, enable_compact=True):
        self.total_size = total_size
        self.blocks = [
            MemoryBlock(0, 20), MemoryBlock(20, 20), MemoryBlock(40, 20),
            MemoryBlock(60, 30), MemoryBlock(90, 30),
            MemoryBlock(120, 40), MemoryBlock(160, 40),
        ]
        # 改为记录上次分配的内存地址，而不是索引
        self.last_alloc_address = 0

        # 新增：控制合并和紧凑功能的开关
        self.enable_merge = enable_merge
        self.enable_compact = enable_compact

        # 记录当前使用的策略，用于优化数据结构重建
        self.current_strategy = None


        print("💾 内存管理器初始化完成")

    def set_merge_enabled(self, enabled):
        """设置是否启用内存合并功能"""
        self.enable_merge = enabled
        print(f"🔧 内存合并功能: {'启用' if enabled else '禁用'}")

    def set_compact_enabled(self, enabled):
        """设置是否启用内存紧凑功能"""
        self.enable_compact = enabled
        print(f"🔧 内存紧凑功能: {'启用' if enabled else '禁用'}")

    def allocate(self, job_size, strategy='first_fit', job_id=None):
        # 记录当前策略
        self.current_strategy = strategy

        addr = self._allocate_once(job_size, strategy, job_id)
        if addr is not None:
            return addr

        # 只有启用紧凑功能时才执行紧凑操作
        if self.enable_compact:
            print("⚠️ 分配失败，尝试执行紧凑...")
            self.compact()
            return self._allocate_once(job_size, strategy, job_id)
        else:
            print("❌ 分配失败，紧凑功能已禁用")
            return None

    def _allocate_once(self, job_size, strategy, job_id):
        if strategy == 'first_fit':
            return self.first_fit(job_size, job_id)
        elif strategy == 'next_fit':
            return self.next_fit(job_size, job_id)
        elif strategy == 'best_fit':
            return self.best_fit(job_size, job_id)
        elif strategy == 'worst_fit':
            return self.worst_fit(job_size, job_id)
        return None

    def first_fit(self, size, job_id):
        for block in self.blocks:
            if block.status == 'free' and block.size >= size:
                return self.split_block(block, size, job_id)
        return None

    def next_fit(self, size, job_id):
        """
        Next Fit算法：从上次分配的地址开始搜索，如果到末尾没找到，再从头开始
        """
        # 首先从上次分配地址开始向后搜索
        for block in self.blocks:
            if (block.status == 'free' and
                    block.start >= self.last_alloc_address and
                    block.size >= size):
                addr = self.split_block(block, size, job_id)
                if addr is not None:
                    self.last_alloc_address = addr  # 更新上次分配地址
                    print(f"🎯 Next Fit: 从地址 {self.last_alloc_address}MB 开始分配 {size}MB")
                    return addr

        # 如果从上次位置到末尾没找到合适的块，从头开始搜索到上次位置
        for block in self.blocks:
            if (block.status == 'free' and
                    block.start < self.last_alloc_address and
                    block.size >= size):
                addr = self.split_block(block, size, job_id)
                if addr is not None:
                    self.last_alloc_address = addr  # 更新上次分配地址
                    print(f"🎯 Next Fit: 环绕到头部，从地址 {self.last_alloc_address}MB 开始分配 {size}MB")
                    return addr

        return None

    def best_fit(self, size, job_id):
        candidates = [b for b in self.blocks if b.status == 'free' and b.size >= size]
        if not candidates:
            return None
        best = min(candidates, key=lambda b: b.size)
        return self.split_block(best, size, job_id)

    def worst_fit(self, size, job_id):
        candidates = [b for b in self.blocks if b.status == 'free' and b.size >= size]
        if not candidates:
            return None
        worst = max(candidates, key=lambda b: b.size)
        return self.split_block(worst, size, job_id)

    def split_block(self, block, size, job_id):
        if block.size == size:
            block.status = 'used'
            block.job_id = job_id
            return block.start
        else:
            new_used = MemoryBlock(block.start, size, 'used', job_id)
            new_free = MemoryBlock(block.start + size, block.size - size, 'free')
            index = self.blocks.index(block)
            self.blocks.pop(index)
            self.blocks.insert(index, new_free)
            self.blocks.insert(index, new_used)
            return new_used.start

    def recycle(self, job_id):
        recycled_block = None
        for block in self.blocks:
            if block.status == 'used' and block.job_id == job_id:
                block.status = 'free'
                block.job_id = None
                recycled_block = block
                print(f"🗑 释放作业 {job_id} 占用的内存块: 地址 {block.start}MB, 大小 {block.size}MB")
                break

        # 只有启用合并功能时才执行合并操作
        if self.enable_merge:
            # 在合并前保存当前的last_alloc_address，确保它仍然有效
            old_address = self.last_alloc_address
            merged_block = self.merge_free_blocks()
            # 合并后检查last_alloc_address是否仍然有效
            self.validate_last_alloc_address(old_address)
        else:
            print("ℹ️ 内存合并功能已禁用，跳过合并操作")

    def validate_last_alloc_address(self, old_address):
        """
        验证并更新last_alloc_address，确保它指向一个有效的位置
        """
        # 找到大于等于old_address的第一个块的起始地址
        valid_addresses = [block.start for block in self.blocks if block.start >= old_address]

        if valid_addresses:
            # 如果有大于等于原地址的块，使用最小的那个
            self.last_alloc_address = min(valid_addresses)
        else:
            # 如果没有，说明原地址超过了所有块，重置为0（从头开始）
            self.last_alloc_address = 0

        if self.current_strategy == 'next_fit':  # 只有next_fit才输出地址更新信息
            print(f"🔄 Next Fit地址更新: {old_address}MB -> {self.last_alloc_address}MB")

    def merge_free_blocks(self):
        """
        合并相邻的空闲内存块，返回是否发生了合并
        """
        print("🔗 开始合并相邻的空闲内存块...")

        # 按起始地址排序
        self.blocks.sort(key=lambda b: b.start)

        merged = []
        i = 0
        has_merged = False

        while i < len(self.blocks):
            current = self.blocks[i]

            # 如果当前块是空闲的，尝试与后续相邻的空闲块合并
            if current.status == 'free':
                while (i + 1 < len(self.blocks) and
                       self.blocks[i + 1].status == 'free' and
                       current.start + current.size == self.blocks[i + 1].start):
                    next_block = self.blocks[i + 1]
                    print(
                        f"  合并: [{current.start}MB, {current.size}MB] + [{next_block.start}MB, {next_block.size}MB]")
                    current.size += next_block.size
                    has_merged = True
                    i += 1
                if has_merged:
                    print(f"  合并结果: [{current.start}MB, {current.size}MB]")

            merged.append(current)
            i += 1

        self.blocks = merged
        if has_merged:
            print("✅ 内存块合并完成")
        else:
            print("ℹ️ 没有相邻的空闲块需要合并")

        return has_merged

    def compact(self):
        new_blocks = []
        current_start = 0

        # 只紧凑原始 block 中的 used 区域
        for block in self.blocks:
            if block.status == 'used':
                new_blocks.append(MemoryBlock(current_start, block.size, 'used', block.job_id))
                current_start += block.size

        # 计算剩下的空闲大小（但最多不超过原始块总和）
        # 限制总内存不能超过已有 block 的和（最多200MB）
        defined_total = sum(b.size for b in self.blocks)
        remaining = defined_total - current_start

        if remaining > 0:
            new_blocks.append(MemoryBlock(current_start, remaining, 'free'))

        self.blocks = new_blocks
        # 紧凑后重置next_fit的起始位置
        self.last_alloc_address = 0
        print("🧹 内存整理完成（紧凑操作）")