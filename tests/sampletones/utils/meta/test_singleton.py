import threading

from sampletones.utils.meta import SingletonMeta


class TestSingleton:
    def test_single_instance_created(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            def __init__(self) -> None:
                pass

        instance1 = TestClass()
        instance2 = TestClass()

        assert instance1 is instance2

    def test_init_called_only_once(self) -> None:
        call_count = 0

        class TestClass(metaclass=SingletonMeta):
            def __init__(self) -> None:
                nonlocal call_count
                call_count += 1

        instance1 = TestClass()
        instance2 = TestClass()

        assert instance1 is instance2
        assert call_count == 1

    def test_init_arguments_only_used_on_first_call(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            def __init__(self, value: int) -> None:
                self.value = value

        instance1 = TestClass(42)
        instance2 = TestClass(100)

        assert instance1 is instance2
        assert instance1.value == 42
        assert instance2.value == 42

    def test_different_classes_have_separate_instances(self) -> None:
        class ClassA(metaclass=SingletonMeta):
            pass

        class ClassB(metaclass=SingletonMeta):
            pass

        instance_a = ClassA()
        instance_b = ClassB()

        assert instance_a is not instance_b
        assert type(instance_a) != type(instance_b)

    def test_subclasses_have_separate_instances(self) -> None:
        class Parent(metaclass=SingletonMeta):
            pass

        class Child(Parent):
            pass

        parent_instance = Parent()
        child_instance = Child()

        assert parent_instance is not child_instance
        assert type(parent_instance) != type(child_instance)

    def test_clear_instances(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            def __init__(self, value: int) -> None:
                self.value = value

        instance1 = TestClass(42)
        TestClass.clear_instances()
        instance2 = TestClass(100)

        assert instance1 is not instance2
        assert instance1.value == 42
        assert instance2.value == 100

    def test_clear_instance(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            def __init__(self, value: int) -> None:
                self.value = value

        instance1 = TestClass(42)
        TestClass.clear_instance(TestClass)
        instance2 = TestClass(100)

        assert instance1 is not instance2
        assert instance1.value == 42
        assert instance2.value == 100

    def test_thread_safety(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            def __init__(self) -> None:
                pass

        instances = []

        def create_instance() -> None:
            instances.append(TestClass())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(instances) == 10
        assert all(instance is instances[0] for instance in instances)

    def test_clear_instance_does_not_affect_other_classes(self) -> None:
        class ClassA(metaclass=SingletonMeta):
            pass

        class ClassB(metaclass=SingletonMeta):
            pass

        instance_a1 = ClassA()
        instance_b1 = ClassB()

        ClassA.clear_instance(ClassA)

        instance_a2 = ClassA()
        instance_b2 = ClassB()

        assert instance_a1 is not instance_a2
        assert instance_b1 is instance_b2

    def test_each_class_has_separate_instances_dict(self) -> None:
        class ClassA(metaclass=SingletonMeta):
            pass

        class ClassB(metaclass=SingletonMeta):
            pass

        ClassA()
        ClassB()

        assert ClassA._instances is not ClassB._instances
        assert ClassA in ClassA._instances
        assert ClassB in ClassB._instances
        assert ClassB not in ClassA._instances
        assert ClassA not in ClassB._instances

    def test_get_instance_returns_none_before_creation(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            pass

        assert TestClass.get_instance() is None

    def test_get_instance_returns_instance_after_creation(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            pass

        instance = TestClass()
        assert TestClass.get_instance() is instance

    def test_has_instance_returns_false_before_creation(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            pass

        assert not TestClass.has_instance()

    def test_has_instance_returns_true_after_creation(self) -> None:
        class TestClass(metaclass=SingletonMeta):
            pass

        TestClass()
        assert TestClass.has_instance()
        assert TestClass.has_instance()
